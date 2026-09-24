cmake_minimum_required(VERSION 3.22.1)
project(djaeger_r89_compat)

add_library(djaeger_r89_compat SHARED module.cpp)
target_compile_features(djaeger_r89_compat PRIVATE cxx_std_17)
target_compile_options(djaeger_r89_compat PRIVATE -Wall -Wextra -Werror=return-type)
find_library(log-lib log)
target_link_libraries(djaeger_r89_compat ${log-lib})
