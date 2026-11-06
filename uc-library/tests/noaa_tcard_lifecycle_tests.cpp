#include "presonus/noaa/card.hpp"
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <new>
#include <string>
#include <type_traits>
using namespace Presonus::NOAA;
using namespace presonus::noaa;
namespace presonus::noaa {
struct CardLifecycleAccess {
  static CardState &state(TCard &card) { return card.state_; }
  static bool owned(TCard &card) {
    return card.ownedRuntime_ && card.ownedState_ && card.registered_;
  }
};
} // namespace presonus::noaa
static unsigned registrations, unregistrations, rootDeletes;
static void *root;
static bool failSpiAllocation;
static std::string expectedImage;
static unsigned checkedNativeProjections;
static void checkProjection(TCard &card, bool seed, unsigned byte = 0) {
  auto &s = CardLifecycleAccess::state(card);
  // Explicit logical projection only. Native padding/vptr/base storage never
  // becomes a host layout claim. Every numeric application word is compared.
  std::pair<unsigned, std::uint32_t *> words[] = {
      {0x10, &s.observedWord10}, {0x14, &s.observedWord14},
      {0x18, &s.observedWord18}, {0x1c, &s.observedWord1c},
      {0x20, &s.observedWord20}, {0x24, &s.observedWord24},
      {0x28, &s.observedWord28}, {0x30, &s.observedWord30},
      {0x34, &s.observedWord34}, {0x38, &s.observedWord38},
      {0x3c, &s.observedWord3c}, {0x40, &s.observedWord40},
      {0x44, &s.observedWord44}, {0x4c, &s.observedWord4c},
      {0x50, &s.observedWord50}, {0x54, &s.observedWord54},
      {0x58, &s.observedWord58}};
  for (auto [offset, value] : words) {
    if (seed)
      *value = byte * 0x01010101u;
    else {
      std::uint32_t native = 0;
      for (unsigned i = 0; i < 4; ++i)
        native |=
            std::stoul(expectedImage.substr(2 * (offset + i), 2), nullptr, 16)
            << (8 * i);
      assert(*value == native);
    }
  }
  if (seed)
    s.observedByte48 = byte;
  else {
    assert(s.observedByte48 ==
           std::stoul(expectedImage.substr(2 * 0x48, 2), nullptr, 16));
    ++checkedNativeProjections;
  }
}

extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t n) {
  if (failSpiAllocation && n == sizeof(TCardSPI))
    throw std::bad_alloc();
  return __real__Znwm(n);
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == root) {
    ++rootDeletes;
    root = nullptr;
  }
  __real__ZdlPv(p);
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == root) {
    ++rootDeletes;
    root = nullptr;
  }
  __real__ZdlPvm(p, n);
}
extern "C" void
__real__ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *, ISysexReceiver *);
extern "C" void
__wrap__ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *spi, ISysexReceiver *receiver) {
  ++registrations;
  __real__ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE(
      spi, receiver);
  auto &v = SpiServiceAccess::state(*spi).receivers;
  assert(v.contains(receiver));
}
extern "C" void
__real__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *, ISysexReceiver *);
extern "C" void
__wrap__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *spi, ISysexReceiver *receiver) {
  ++unregistrations;
  if (!expectedImage.empty())
    checkProjection(*dynamic_cast<TCard *>(receiver), false);
  __real__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE(
      spi, receiver);
  assert(!SpiServiceAccess::state(*spi).receivers.contains(receiver));
}
struct Pins final : presonus::surface_panel_port::InputPinIO {
  std::FILE *open(const char *, const char *) override { return nullptr; }
  void log(const char *) override {}
  int printPin(std::FILE *, const char *, int) override { std::abort(); }
  int close(std::FILE *) override { std::abort(); }
  void formatPath(char *, std::size_t, const char *, int) override {
    std::abort();
  }
  std::size_t write(const void *, std::size_t, std::size_t,
                    std::FILE *) override {
    std::abort();
  }
  int buffering(std::FILE *, char *, int, std::size_t) override {
    std::abort();
  }
  void rewind(std::FILE *) override { std::abort(); }
  int flush(std::FILE *) override { std::abort(); }
  int get(std::FILE *) override { std::abort(); }
  void notify(Presonus::Panel::PinStateObserver *, int, int) override {
    std::abort();
  }
};
struct IO final : SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const SpiTransfer &) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
};
struct Pump final : presonus::dice::IdlePump {
  void onIdle(bool) override { std::abort(); }
};
struct Concrete final : TCard {
  using TCard::TCard;
  std::int32_t updateFirmware(Presonus::UC::IFirmwareUpdateListener *,
                              int) override {
    std::abort();
  }
};
extern "C" void cardD0(TCard *) asm("_ZN8Presonus4NOAA5TCardD0Ev");
extern "C" void cardD1(TCard *) asm("_ZN8Presonus4NOAA5TCardD1Ev");
extern "C" void cardD2(TCard *) asm("_ZN8Presonus4NOAA5TCardD2Ev");
static void defaults(TCard &c) {
  auto &s = CardLifecycleAccess::state(c);
  assert(CardLifecycleAccess::owned(c));
  assert(s.observedWord10 == 0xffffffffu && s.observedWord14 == 0xffffffffu);
  assert(!s.observedWord18 && !s.observedWord1c && !s.observedWord20 &&
         !s.observedWord24 && !s.observedWord28);
  assert(!s.observedWord30 && !s.observedWord34 && !s.observedWord38 &&
         !s.observedWord3c);
  assert(!s.observedWord40 && !s.observedWord44 && !s.observedByte48 &&
         !s.observedWord4c && !s.observedWord50 && !s.observedWord54 &&
         !s.observedWord58);
  assert(!s.opaque2c.value && !s.opaque5c.value && !s.expectedSerial);
  assert(c.portableState().command == 0 && c.portableState().status == 0 &&
         c.portableState().infoWords[0] == 0);
  c.portableState().command = 1;
  assert(c.waitAck(500) == 1); // actual bound CCL clock and response provider
}
int main(int argc, char **argv) {
  assert(argc == 2);
  static_assert(!std::is_abstract_v<TCard>);
  static Pins pins;
  static IO io;
  presonus::surface_panel_port::setInputPinConstructionIO(&pins);
  setSpiServiceConstructionIO(&io); // both captured before first lazy singleton
  std::ifstream in(argv[1]);
  assert(in);
  std::string variant, image, events;
  unsigned lazy, seed, deletes, cases = 0;
  while (in >> variant >> lazy >> seed >> deletes >> image >> events) {
    SpiPacketState borrowed({}, 0, 0, 0);
    TCardSPI spi(borrowed);
    SpiServiceAccess::singleton(lazy ? nullptr : &spi);
    unsigned r = registrations, u = unregistrations, d = rootDeletes;
    auto *c = new Concrete;
    root = c;
    defaults(*c);
    expectedImage = image;
    if (variant == "C1" || variant == "C2")
      checkProjection(*c, false);
    else
      checkProjection(*c, true, seed);
    assert(registrations == r + 1);
    auto *before = SpiServiceAccess::singleton();
    assert(before);
    if (variant == "C1" || variant == "C2") {
      // Concrete derived construction exercises base construction; both exact
      // original constructor variants are independently run by native oracle.
      delete c;
    } else {
      // Repeat destructor lazy branch after original singleton reset.
      if (lazy)
        SpiServiceAccess::singleton(nullptr);
      if (variant == "D0")
        cardD0(c);
      else {
        if (variant == "D1")
          cardD1(c);
        else
          cardD2(c);
        assert(rootDeletes == d);
        root = nullptr;
        ::operator delete(c);
      }
    }
    assert(unregistrations == u + 1);
    assert(
        rootDeletes ==
        d + ((variant == "D0" || variant == "C1" || variant == "C2") ? 1 : 0));
    SpiServiceAccess::singleton(nullptr);
    expectedImage.clear();
    ++cases;
  }
  assert(checkedNativeProjections == cases + 12);
  // Borrowed state is neither registered nor released by compatibility setup.
  Pump pump;
  presonus::dice::CclResponseServices response(pump);
  CardState state{};
  state.observedWord14 = 17;
  unsigned r = registrations, u = unregistrations;
  {
    Concrete c(cardSetupTag, state, response, io);
    assert(!CardLifecycleAccess::owned(c));
    assert(!c.isMounted());
  }
  assert(registrations == r && unregistrations == u &&
         state.observedWord14 == 17);
  // Real host allocation failure unwinds owned members before registration.
  failSpiAllocation = true;
  bool caught = false;
  try {
    Concrete c;
  } catch (const std::bad_alloc &) {
    caught = true;
  }
  failSpiAllocation = false;
  assert(caught && registrations == r && !SpiServiceAccess::singleton());
  std::cout << cases
            << " native fixture rows; actual CCL vectors, lazy recreation, "
               "host D0 freeing, borrowed and allocation failure passed\n";
}
