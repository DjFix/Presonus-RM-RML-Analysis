#include "core/system/corethread.h"
#include "core/system/coretime.h"
#include "presonus/uux/FirmwareUpdaterPaths.hpp"
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <sys/wait.h>
#include <system_error>
#include <unistd.h>
namespace Presonus::UUX {
int FirmwareUpdater::executeBashUpgradeScript(const char *command) {
  const pid_t process = ::fork();
  if (process < 0)
    return 0; // Original failure behavior preserved, not changed to -1.
  if (process != 0)
    return process;
  static_assert((-1 >> 8) == -1);
  std::exit(::system(command) >> 8);
}
int FirmwareUpdater::spinUpgradeDisplay(int process) {
  // Original converts seconds to int64, uses low32 and wraps deadline addition.
  const auto start = static_cast<std::int64_t>(Core::SystemClock::getSeconds());
  const std::uint32_t deadlineBits = static_cast<std::uint32_t>(start) + 800u;
  std::int32_t deadline;
  std::memcpy(&deadline, &deadlineBits, sizeof deadline);
  Core::CString128 message("Please wait");
  float progress = 0.03125f;
  int status = 0;
  for (;;) {
    const pid_t result = ::waitpid(process, &status, WNOHANG);
    if (result < 0) {
      // The original may read an uninitialized status byte here. Explicit
      // source-port failure, outside claimed original-equivalence domain.
      throw std::system_error(errno, std::generic_category(), "waitpid");
    }
    if (result != 0)
      break;
    if (static_cast<double>(deadline) <= Core::SystemClock::getSeconds())
      return 8; // Original does not kill/reap on timeout.
    if (animate)
      message += ".";
    progress += 0.008333333767950535f;
    if (listener)
      listener->onProgress("Applying firmware update.", message.str(),
                           progress);
    Core::Threads::CurrentThread::sleep(1000);
  }
  if (listener)
    listener->onProgress("Applying firmware update.", message.str(), 100.f);
  // Original reads the second raw status byte without checking WIFEXITED.
  return (static_cast<std::uint32_t>(status) >> 8) & 255u;
}
} // namespace Presonus::UUX
