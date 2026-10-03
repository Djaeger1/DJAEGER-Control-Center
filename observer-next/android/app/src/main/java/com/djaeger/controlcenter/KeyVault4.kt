package com.djaeger.controlcenter
import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
class KeyVault4(private val context:Context){private val alias="djaeger_cc_vault4_aes";private val prefs=context.getSharedPreferences("djaeger_cc_vault4",Context.MODE_PRIVATE);private fun key():SecretKey{val ks=KeyStore.getInstance("AndroidKeyStore").apply{load(null)};val e=ks.getEntry(alias,null) as? KeyStore.SecretKeyEntry;if(e!=null)return e.secretKey;val kg=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");kg.init(KeyGenParameterSpec.Builder(alias,KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());return kg.generateKey()}
fun put(slot:Int,value:String){require(slot in 1..4);require(value.isNotBlank());val c=Cipher.getInstance("AES/GCM/NoPadding");c.init(Cipher.ENCRYPT_MODE,key());prefs.edit().putString("s$slot",Base64.encodeToString(c.iv,Base64.NO_WRAP)+":"+Base64.encodeToString(c.doFinal(value.toByteArray()),Base64.NO_WRAP)).apply()}
fun get(slot:Int):String?{require(slot in 1..4);val raw=prefs.getString("s$slot",null)?:return null;return runCatching{val p=raw.split(":",limit=2);val c=Cipher.getInstance("AES/GCM/NoPadding");c.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,Base64.decode(p[0],Base64.NO_WRAP)));String(c.doFinal(Base64.decode(p[1],Base64.NO_WRAP)))}.getOrNull()}
fun delete(slot:Int){require(slot in 1..4);prefs.edit().remove("s$slot").apply()}
private fun meta()=context.getSharedPreferences("djaeger_cc_vault4_meta",Context.MODE_PRIVATE)
fun active():Int=meta().getInt("active",1).coerceIn(1,4)
fun setActive(slot:Int){require(slot in 1..4);meta().edit().putInt("active",slot).apply()}
fun cooldown(slot:Int,until:Long){require(slot in 1..4);meta().edit().putLong("cooldown_$slot",until).apply()}
fun cooldownUntil(slot:Int):Long=meta().getLong("cooldown_$slot",0L)
fun nextSlot(now:Long=System.currentTimeMillis()/1000):Int?{val a=active();for(step in 1..4){val s=((a-1+step)%4)+1;if(get(s)!=null&&cooldownUntil(s)<=now)return s};return null}
fun configuredKeys(): List<String> = (1..4).mapNotNull { get(it) }
fun rotationStatus():String=(1..4).joinToString(" • "){s->val u=cooldownUntil(s);"KEY $s: "+if(get(s)==null)"EMPTY" else if(u>System.currentTimeMillis()/1000)"COOLDOWN" else if(s==active())"ACTIVE" else "READY"}
fun status():String=(1..4).joinToString(" • "){"KEY $it: "+if(prefs.contains("s$it"))"•••• SAVED" else "EMPTY"}}
