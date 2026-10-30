#include "presonus/noaa/spi_packets.hpp"

namespace {
// Only this fixture unit instantiates the actual SDK PosixLock, whose pinned
// prebuilt provider has no RTTI. Keep ASan/other UBSan; isolate its vptr
// exception so the separate lifecycle/RTTI fixture retains vptr
// instrumentation.
struct BorrowedSpiFixture {
  presonus::noaa::SpiPacketState state{{}, 0, 0, 16};
  Presonus::NOAA::TCardSPI spi{state};
};
} // namespace

extern "C" void *makeBorrowedSpiFixture() { return new BorrowedSpiFixture; }
extern "C" Presonus::NOAA::TCardSPI *borrowedSpiFixture(void *fixture) {
  return &static_cast<BorrowedSpiFixture *>(fixture)->spi;
}
extern "C" presonus::noaa::SpiPacketState *borrowedSpiState(void *fixture) {
  return &static_cast<BorrowedSpiFixture *>(fixture)->state;
}
extern "C" void destroyBorrowedSpiFixture(void *fixture) {
  delete static_cast<BorrowedSpiFixture *>(fixture);
}
