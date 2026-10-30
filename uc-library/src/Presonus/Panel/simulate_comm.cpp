#include "presonus/panel/simulate_comm.hpp"
#include <cstring>

namespace Presonus::Panel {
char *SimulateComm::s_buffer1 = nullptr;
char *SimulateComm::s_buffer2 = nullptr;
std::uint32_t SimulateComm::s_instances = 0;

SimulateComm::SimulateComm(bool direction) {
  if (++s_instances == 1) {
    s_buffer1 = new char[0x19000];
    s_buffer2 = new char[0x19000];
  }
  readBuffer_ = direction ? s_buffer1 : s_buffer2;
  writeBuffer_ = direction ? s_buffer2 : s_buffer1;
}

SimulateComm::~SimulateComm() {
  Core::Threads::ScopedLock guard(lock_);
  if (--s_instances == 0) {
    delete[] s_buffer1;
    delete[] s_buffer2;
    // Original leaves these static pointers unchanged after deallocation.
  }
}

int SimulateComm::open(const char *) {
  Core::Threads::ScopedLock guard(lock_);
  readBuffer_[0] = 0;
  writeBuffer_[0] = 0;
  return 1;
}

void SimulateComm::close() {}
int SimulateComm::enableHISpeed(bool) { return 0; }

int SimulateComm::write(const char *source, int count) {
  Core::Threads::ScopedLock guard(lock_);
  std::strncat(writeBuffer_, source, static_cast<std::uint32_t>(count));
  return count;
}

int SimulateComm::read(char *destination, int count) {
  Core::Threads::ScopedLock guard(lock_);
  destination[0] = 0;
  const auto length = std::strlen(readBuffer_);
  const auto requested = static_cast<std::uint32_t>(count);
  if (length < requested)
    return 0;
  std::strncpy(destination, readBuffer_, requested);
  const auto remainder = length - requested;
  std::memmove(readBuffer_, readBuffer_ + requested, remainder);
  readBuffer_[remainder] = 0;
  return count;
}
} // namespace Presonus::Panel
