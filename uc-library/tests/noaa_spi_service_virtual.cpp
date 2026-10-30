#include "presonus/noaa/spi_packets.hpp"
#include <cstring>
#include <new>
namespace presonus::noaa::testing {
struct Derived : Presonus::NOAA::TCardSPI {};
} // namespace presonus::noaa::testing
extern "C" std::size_t spiDerivedSize() {
  return sizeof(presonus::noaa::testing::Derived);
}
extern "C" Presonus::NOAA::TCardSPI *spiDerivedRootAddress(void *storage) {
  return static_cast<presonus::noaa::testing::Derived *>(storage);
}
extern "C" Presonus::NOAA::TCardSPI *spiConstructDerived(void *storage) {
  return new (storage) presonus::noaa::testing::Derived;
}
extern "C" void spiDestroyDerived(Presonus::NOAA::TCardSPI *p) {
  using presonus::noaa::testing::Derived;
  static_cast<Derived *>(p)->Derived::~Derived();
}
// Independent native ABI test entry points in a separate non-LTO TU.
extern "C" void spiNativeD1(Presonus::NOAA::TCardSPI *p) {
  void **vptr;
  std::memcpy(&vptr, p, sizeof(vptr));
  reinterpret_cast<void (*)(Presonus::NOAA::TCardSPI *)>(vptr[0])(p);
}
extern "C" void spiNativeD0(Presonus::NOAA::TCardSPI *p) {
  void **vptr;
  std::memcpy(&vptr, p, sizeof(vptr));
  reinterpret_cast<void (*)(Presonus::NOAA::TCardSPI *)>(vptr[1])(p);
}
