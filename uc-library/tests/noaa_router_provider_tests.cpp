#include "core/system/coretime.h"
#include "presonus/noaa/router.hpp"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
using namespace presonus::noaa;
using namespace presonus::dice;
using namespace Presonus::NOAA;
static unsigned errors;
static std::vector<std::string> diagnostics;
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  char text[256];
  va_list args;
  va_start(args, format);
  std::vsnprintf(text, sizeof text, format, args);
  va_end(args);
  assert(std::strcmp(text, "route err found") == 0 ||
         std::strcmp(text, "**ERR SPI\n") == 0);
  diagnostics.emplace_back(text);
  ++errors;
}
struct IO final : SpiServiceIO {
  explicit IO(SpiServiceIO &actualDiagnostic, bool zero)
      : diagnostic_(actualDiagnostic), zero_(zero) {}
  bool zero_;
  SpiServiceIO &diagnostic_;
  unsigned transfers = 0;
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int descriptor, const SpiTransfer &transfer) override {
    assert(descriptor == 71 && transfer.length == 3);
    assert(transfer.tx[0] == 0xf0 && transfer.tx[1] == 0x16 &&
           transfer.tx[2] == 0xf7);
    ++transfers;
    if (zero_)
      return 0;
    transfer.rx[0] = 0xf8;
    return 1;
  }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { return Core::SystemClock::getTime(); }
  void diagnostic(bool out, const char *format, int value, bool arg) override {
    diagnostic_.diagnostic(out, format, value, arg);
  }
};
struct Pump final : IdlePump {
  TCardRouter *router = nullptr;
  unsigned pumps = 0;
  void onIdle(bool force) override {
    assert(!force && router != nullptr);
    ++pumps;
    router->portableState().command = 0x16;
    router->portableState().status = 0; // force the caller's error branch
  }
};
int main(int argc, char **) {
  bool zero = argc > 1;
  auto &actualDiagnostic = spiServiceConstructionIO();
  IO io(actualDiagnostic, zero);
  auto *previous = setSpiServiceConstructionIO(&io);
  SpiPacketState state(std::array<unsigned char, 256>{}, 0, 0, 0);
  {
    TCardSPI spi(state);
    auto *priorSingleton = SpiServiceAccess::singleton();
    SpiServiceAccess::singleton(&spi);
    SpiServiceAccess::bind(spi, io, 71, {}, 0);
    Pump pump;
    CclResponseServices response(pump);
    RouterState bytes{};
    TCardRouter router(bytes, response, actualDiagnostic,
                       rm13731LinkAddressRouterLookup());
    pump.router = &router;
    const auto before = Core::SystemClock::getTime();
    router.doRouteCommands(nullptr, 0, 0);
    const auto after = Core::SystemClock::getTime();
    assert(after >= before && io.transfers == 1 && pump.pumps == 1 &&
           errors == (zero ? 2u : 1u));
  }
  assert(diagnostics.back() == "route err found");
  if (zero)
    assert(diagnostics.front() == "**ERR SPI\n");
  setSpiServiceConstructionIO(previous);
  if (zero)
    std::puts("{\"passed\":true,\"spi_zero_result_regression\":true,\"ordered_"
              "diagnostics\":2,\"physical_operations\":0}");
  else
    std::puts("{\"passed\":true,\"real_ccl_clock_wait_and_diagnostic\":true,"
              "\"real_noaa_post_spi_provider\":true,\"simulated_transfers\":1,"
              "\"physical_operations\":0}");
}
