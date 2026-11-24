#include "presonus/panel/SharedMemoryComm.hpp"

#include <cstdio>

int main() {
  Presonus::Panel::SharedMemoryComm comm;
  std::printf("%d\n", comm.enableHISpeed(false));
  std::printf("%d\n", comm.enableHISpeed(true));
}
