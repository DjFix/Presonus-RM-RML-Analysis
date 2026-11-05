#include "presonus/noaa/TCardFPGAUpdater.hpp"
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>
using Presonus::NOAA::TCardFPGAUpdater;
struct Listener final : Presonus::UC::IFirmwareUpdateListener {
  unsigned calls = 0, bits = 0;
  std::string message;
  bool null = false;
  void onProgress(const char *s, float p) override {
    ++calls;
    std::memcpy(&bits, &p, 4);
    null = !s;
    message = s ? s : "";
  }
};
struct Services final : presonus::noaa::FpgaUpdaterServices {
  std::int64_t raw = 0;
  std::string debug;
  std::vector<unsigned> sleeps;
  std::int64_t clockRawTicks() override { return raw; }
  void pumpIdle(bool) override { throw std::runtime_error("unexpected pump"); }
  void sleepMilliseconds(std::uint32_t x) override { sleeps.push_back(x); }
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {
    throw std::runtime_error("unexpected timeout");
  }
  void debugMessage(const char *s) override { debug += s; }
};
extern "C" void
ctor1(void *, Presonus::UC::IFirmwareUpdateListener *,
      Presonus::FirmwareBundle
          *) asm("_ZN8Presonus4NOAA16TCardFPGAUpdaterC1EPNS_"
                 "2UC23IFirmwareUpdateListenerEPNS_14FirmwareBundleE");
extern "C" void
ctor2(void *, Presonus::UC::IFirmwareUpdateListener *,
      Presonus::FirmwareBundle
          *) asm("_ZN8Presonus4NOAA16TCardFPGAUpdaterC2EPNS_"
                 "2UC23IFirmwareUpdateListenerEPNS_14FirmwareBundleE");
extern "C" void dtor1(void *) asm("_ZN8Presonus4NOAA16TCardFPGAUpdaterD1Ev");
extern "C" void dtor2(void *) asm("_ZN8Presonus4NOAA16TCardFPGAUpdaterD2Ev");
void check(bool ok) {
  if (!ok)
    throw std::runtime_error("fixture mismatch");
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  presonus::noaa::SpiPacketState state({}, 0, 0, 4);
  Presonus::NOAA::TCardSPI spi(state);
  presonus::noaa::SpiServiceAccess::singleton(&spi);
  std::ifstream input(argv[1]);
  check(bool(input));
  int mode;
  unsigned count = 0;
  while (input >> mode) {
    if (mode == 3) {
      int target, reg, unreg;
      input >> target >> reg >> unreg;
      alignas(TCardFPGAUpdater) unsigned char storage[sizeof(TCardFPGAUpdater)];
      Listener listener;
      (target == 8 ? ctor2 : ctor1)(storage, &listener, nullptr);
      auto *p = std::launder(reinterpret_cast<TCardFPGAUpdater *>(storage));
      check(state.receivers.count() == 1 && state.receivers[0] == p);
      check(!p->portableState().command && !p->portableState().status &&
            !p->portableState().infoWords[0]);
      (target == 10 ? dtor2 : dtor1)(p);
      check(state.receivers.count() == 0);
      check((target < 9 && reg == 1 && unreg == 0) ||
            (target >= 9 && reg == 0 && unreg == 1));
    } else {
      Listener listener;
      Services services;
      int target = 0, hasListener = 0, message = 0;
      unsigned bits = 0, debug = 0, sleeps = 0;
      std::int64_t epoch = 0;
      if (mode == 2)
        input >> target >> hasListener >> message >> services.raw >> epoch >>
            bits >> debug >> sleeps;
      TCardFPGAUpdater updater(hasListener ? &listener : nullptr, nullptr);
      updater.setPortableServices(services);
      if (mode == 0) {
        unsigned length, command, result;
        input >> length >> command >> result;
        Presonus::NOAA::SysexPacket packet;
        packet.length = length;
        packet.bytes[1] = command;
        check(updater.accepts(packet) == bool(result));
      } else if (mode == 1) {
        unsigned a, b, c, x, y, z;
        input >> a >> b >> c >> x >> y >> z;
        Presonus::NOAA::SysexPacket packet;
        packet.length = 0;
        packet.bytes[2] = a;
        packet.bytes[3] = b;
        packet.bytes[4] = c;
        updater.portableState().command = 99;
        updater.portableState().status = 99;
        updater.portableState().infoWords[0] = 0xa5a5a5a5;
        updater.receive(packet);
        auto &s = updater.portableState();
        check(s.command == x && s.infoWords[0] == y && s.status == z);
      } else if (mode == 2) {
        presonus::noaa::setFpgaProgressEpochMilliseconds(epoch);
        const char *text = message == 0 ? nullptr : message == 1 ? "" : "hello";
        if (target == 1)
          updater.printProgress(text);
        else
          updater.printProgressErr(text);
        check(listener.calls == unsigned(hasListener));
        if (hasListener)
          check(listener.bits == bits && listener.null == (text == nullptr) &&
                listener.message == (text ? text : ""));
        check(services.debug == (debug ? "hello\n" : ""));
        check(services.sleeps.size() == sleeps);
        if (sleeps)
          check(services.sleeps[0] == 2000);
      } else
        throw std::runtime_error("unknown case");
    }
    check(bool(input));
    ++count;
  }
  presonus::noaa::SpiServiceAccess::singleton(nullptr);
  std::cout << "PASS " << count
            << " original ARM non-programming fixtures; existing singleton "
               "lifecycle; no update/wait/device operations\n";
}
