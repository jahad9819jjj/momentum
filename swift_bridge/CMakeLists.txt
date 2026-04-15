cmake_minimum_required(VERSION 3.16.3)
project(MomentumSwiftBridge C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---- Find the installed Momentum library ----
# Momentum must be built and installed first (pixi run install)
find_package(momentum CONFIG REQUIRED)

# ---- Build the C bridge as a shared library ----
add_library(MomentumBridge SHARED
  MomentumBridge.cpp
)

target_include_directories(MomentumBridge PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}
)

# Link against the Momentum "umbrella" library which pulls in all sub-targets
target_link_libraries(MomentumBridge PRIVATE
  momentum::character
  momentum::skeleton
  momentum::math
  momentum::io_character
)

# ---- Install ----
install(TARGETS MomentumBridge
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib
  RUNTIME DESTINATION bin
)
install(FILES MomentumBridge.h DESTINATION include)
