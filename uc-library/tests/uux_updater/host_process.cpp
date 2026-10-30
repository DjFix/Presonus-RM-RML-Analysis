#include "process_boundary.hpp"
int main() {
  fixture::requireProductionMethods();
  using namespace fixture;
  const char *commands[] = {"./fw-upgrade.sh", "./fw-local-upgrade.sh",
                            "not executed ; $fixture"};
  unsigned total = 0;
  while (std::cin >> kind) {
    reset();
    Listener listener;
    if (kind == 0) {
      unsigned cmd, expected, child, expectedExit;
      std::cin >> forkBits >> systemBits >> cmd >> expected >> child >>
          expectedExit;
      assert(cmd < 3);
      command = commands[cmd];
      Presonus::UUX::FirmwareUpdater updater(presonus::uux::PathsSourcePort{});
      if (setjmp(jump) == 0) {
        const int result = updater.executeBashUpgradeScript(command);
        assert(!child && static_cast<unsigned>(result) == expected);
      } else {
        assert(child && static_cast<unsigned>(exitCode) == expectedExit);
      }
      assert(forks == 1 && systems == child && exits == child);
    } else {
      assert(kind == 1);
      unsigned expected, expectedCallbacks, expectedWaits, expectedClocks,
          expectedSleeps;
      std::uint64_t expectedHash;
      std::cin >> pidBits >> loops >> animate >> present >> statusBits >>
          startNs >> timeout >> expected >> expectedCallbacks >> expectedHash >>
          expectedWaits >> expectedClocks >> expectedSleeps;
      Presonus::UUX::FirmwareUpdater updater(
          presonus::uux::PathsSourcePort{}, "/unused",
          present ? &listener : nullptr, animate);
      const int result = updater.spinUpgradeDisplay(asInt(pidBits));
      assert(static_cast<unsigned>(result) == expected);
      assert(callbacks == expectedCallbacks && hash == expectedHash);
      assert(waits == expectedWaits && clocks == expectedClocks &&
             sleeps == expectedSleeps);
    }
    ++total;
  }
  assert(total == 3672);
  unsigned errors = 0;
  for (unsigned pid : {0xffffffffu, 0u, 42u})
    for (int error : {ECHILD, EINTR, EINVAL}) {
      reset();
      kind = 1;
      pidBits = pid;
      timeout = 0;
      startNs = 0;
      waitError = error;
      Presonus::UUX::FirmwareUpdater updater(presonus::uux::PathsSourcePort{});
      bool caught = false;
      try {
        updater.spinUpgradeDisplay(asInt(pid));
      } catch (const std::system_error &e) {
        caught = e.code().value() == error;
      }
      assert(caught && waits == 1 && sleeps == 0 && callbacks == 0);
      ++errors;
    }
  std::cout << "PASS original_host_process_cases=" << total
            << " explicit_source_port_error_cases=" << errors << '\n';
}
