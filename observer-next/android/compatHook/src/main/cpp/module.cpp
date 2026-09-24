#include <sys/types.h>
#include "zygisk.hpp"

#include <android/log.h>
#include <fcntl.h>
#include <jni.h>
#include <pthread.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cstring>

#define TAG "DJAEGER_R89_ZCOMPAT"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, TAG, __VA_ARGS__)

namespace {

JavaVM *gVm = nullptr;
void *gDexMap = nullptr;
size_t gDexSize = 0;
int gPineFd = -1;
bool gTarget = false;

bool clearIfException(JNIEnv *env, const char *where) {
    if (!env->ExceptionCheck()) return false;
    env->ExceptionClear();
    LOGE("JNI exception at %s", where);
    return true;
}

void *installThread(void *) {
    if (!gVm || !gDexMap || gDexSize == 0 || gPineFd < 0) return nullptr;

    JNIEnv *env = nullptr;
    if (gVm->AttachCurrentThread(&env, nullptr) != JNI_OK || !env) {
        LOGE("AttachCurrentThread failed");
        return nullptr;
    }

    jobject app = nullptr;
    jclass at = env->FindClass("android/app/ActivityThread");
    if (!at || clearIfException(env, "ActivityThread")) goto out;
    {
        jmethodID currentApp = env->GetStaticMethodID(
                at, "currentApplication", "()Landroid/app/Application;");
        if (!currentApp || clearIfException(env, "currentApplication")) goto out;

        for (int i = 0; i < 120 && !app; ++i) {
            app = env->CallStaticObjectMethod(at, currentApp);
            if (clearIfException(env, "currentApplication call")) app = nullptr;
            if (!app) usleep(100000);
        }
    }
    if (!app) {
        LOGE("Application not ready");
        goto out;
    }

    {
        jclass contextClass = env->FindClass("android/content/Context");
        if (!contextClass || clearIfException(env, "Context")) goto out;
        jmethodID getClassLoader = env->GetMethodID(
                contextClass, "getClassLoader", "()Ljava/lang/ClassLoader;");
        if (!getClassLoader || clearIfException(env, "getClassLoader")) goto out;

        jobject appCl = env->CallObjectMethod(app, getClassLoader);
        if (!appCl || clearIfException(env, "getClassLoader call")) goto out;

        jobject dexBuffer = env->NewDirectByteBuffer(gDexMap, static_cast<jlong>(gDexSize));
        if (!dexBuffer || clearIfException(env, "NewDirectByteBuffer")) goto out;

        jclass imdcl = env->FindClass("dalvik/system/InMemoryDexClassLoader");
        if (!imdcl || clearIfException(env, "InMemoryDexClassLoader")) goto out;
        jmethodID ctor = env->GetMethodID(
                imdcl, "<init>", "(Ljava/nio/ByteBuffer;Ljava/lang/ClassLoader;)V");
        if (!ctor || clearIfException(env, "InMemoryDexClassLoader ctor")) goto out;

        jobject hookCl = env->NewObject(imdcl, ctor, dexBuffer, appCl);
        if (!hookCl || clearIfException(env, "new InMemoryDexClassLoader")) goto out;

        jclass classLoaderClass = env->FindClass("java/lang/ClassLoader");
        jmethodID loadClass = classLoaderClass
                ? env->GetMethodID(classLoaderClass, "loadClass",
                                   "(Ljava/lang/String;)Ljava/lang/Class;")
                : nullptr;
        if (!classLoaderClass || !loadClass || clearIfException(env, "ClassLoader.loadClass")) goto out;

        jstring hookName = env->NewStringUTF("com.djaeger.compat.HookEntry");
        jobject hookClassObj = env->CallObjectMethod(hookCl, loadClass, hookName);
        if (!hookClassObj || clearIfException(env, "load HookEntry")) goto out;

        jclass hookClass = static_cast<jclass>(hookClassObj);
        jmethodID install = env->GetStaticMethodID(
                hookClass, "install",
                "(Landroid/app/Application;Ljava/lang/ClassLoader;I)V");
        if (!install || clearIfException(env, "HookEntry.install")) goto out;

        env->CallStaticVoidMethod(hookClass, install, app, appCl, static_cast<jint>(gPineFd));
        if (clearIfException(env, "HookEntry.install call")) goto out;

        LOGI("compat install dispatched");
    }

out:
    gVm->DetachCurrentThread();
    return nullptr;
}

class DjaegerR89Compat : public zygisk::ModuleBase {
public:
    void onLoad(zygisk::Api *api, JNIEnv *env) override {
        api_ = api;
        env_ = env;
        env_->GetJavaVM(&gVm);
    }

    void preAppSpecialize(zygisk::AppSpecializeArgs *args) override {
        gTarget = false;
        if (!args || !args->nice_name) {
            api_->setOption(zygisk::Option::DLCLOSE_MODULE_LIBRARY);
            return;
        }

        const char *name = env_->GetStringUTFChars(args->nice_name, nullptr);
        if (name) {
            gTarget = std::strcmp(name, "com.djaeger.observer") == 0;
            env_->ReleaseStringUTFChars(args->nice_name, name);
        }
        if (!gTarget) {
            api_->setOption(zygisk::Option::DLCLOSE_MODULE_LIBRARY);
            return;
        }

        int moduleDir = api_->getModuleDir();
        if (moduleDir < 0) {
            LOGE("getModuleDir failed");
            return;
        }

        int dexFd = openat(moduleDir, "hook/classes.dex", O_RDONLY);
        gPineFd = openat(moduleDir, "hook/libpine.so", O_RDONLY);
        close(moduleDir);

        if (dexFd < 0 || gPineFd < 0) {
            LOGE("hook payload open failed dex=%d pine=%d", dexFd, gPineFd);
            if (dexFd >= 0) close(dexFd);
            if (gPineFd >= 0) { close(gPineFd); gPineFd = -1; }
            return;
        }

        struct stat st{};
        if (fstat(dexFd, &st) != 0 || st.st_size <= 0) {
            LOGE("dex fstat failed");
            close(dexFd);
            close(gPineFd);
            gPineFd = -1;
            return;
        }
        gDexSize = static_cast<size_t>(st.st_size);
        gDexMap = mmap(nullptr, gDexSize, PROT_READ, MAP_PRIVATE, dexFd, 0);
        close(dexFd);
        if (gDexMap == MAP_FAILED) {
            gDexMap = nullptr;
            gDexSize = 0;
            close(gPineFd);
            gPineFd = -1;
            LOGE("dex mmap failed");
            return;
        }

        if (!api_->exemptFd(gPineFd)) {
            LOGE("pine fd exempt failed");
            munmap(gDexMap, gDexSize);
            gDexMap = nullptr;
            gDexSize = 0;
            close(gPineFd);
            gPineFd = -1;
        }
    }

    void postAppSpecialize(const zygisk::AppSpecializeArgs *) override {
        if (!gTarget || !gDexMap || gDexSize == 0 || gPineFd < 0) return;
        pthread_t thread{};
        if (pthread_create(&thread, nullptr, installThread, nullptr) == 0) {
            pthread_detach(thread);
        } else {
            LOGE("pthread_create failed");
        }
    }

private:
    zygisk::Api *api_ = nullptr;
    JNIEnv *env_ = nullptr;
};

} // namespace

REGISTER_ZYGISK_MODULE(DjaegerR89Compat)
