#include "presonus/panel/SharedMemoryComm.hpp"

#include <cstdio>

int main() {
  Presonus::Panel::SharedMemoryComm comm;
  std::printf("%d\n", comm.open(nullptr));
  std::printf("%d\n", comm.open(""));
  std::printf("%d\n", comm.open("panel"));
}
