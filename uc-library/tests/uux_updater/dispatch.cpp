#include "process_boundary.hpp"
int main(int argc, char **argv) {
  fixture::requireProductionMethods();
  assert(argc == 4);
  using namespace fixture;
  unsigned method, exists, expected, child, expectedExit;
  unsigned expectedWaits, expectedClocks, expectedSleeps;
  unsigned total = 0;
  while (std::cin >> method >> exists >> forkBits >> systemBits >> statusBits >>
         loops >> expected >> child >> expectedExit >> expectedWaits >>
         expectedClocks >> expectedSleeps) {
    assert(method < 2 && exists < 3);
    reset();
    kind = 1;
    timeout = 0;
    startNs = 0;
    present = 0;
    pidBits = asInt(forkBits) < 0 ? 0 : forkBits;
    command = method == 0 ? "./fw-local-upgrade.sh" : "./fw-upgrade.sh";
    Presonus::UUX::FirmwareUpdater updater(presonus::uux::PathsSourcePort{},
                                           argv[exists + 1]);
    Core::CString256 usb(argv[exists + 1]);
    assert(updater.setUsbImagePath(usb) == 0);
    if (setjmp(jump) == 0) {
      const int result = method == 0 ? updater.doLocalFirmwareUpdate()
                                     : updater.doUsbFirmwareUpdate();
      assert(!child && static_cast<unsigned>(result) == expected);
    } else {
      assert(child && static_cast<unsigned>(exitCode) == expectedExit);
    }
    assert(forks == unsigned(exists != 0) && systems == child &&
           exits == child);
    assert(waits == expectedWaits && clocks == expectedClocks &&
           sleeps == expectedSleeps && callbacks == 0);
    ++total;
  }
  assert(total == 1728);
  std::cerr << "PASS original_composed_dispatch_cases=" << total << '\n';
}
