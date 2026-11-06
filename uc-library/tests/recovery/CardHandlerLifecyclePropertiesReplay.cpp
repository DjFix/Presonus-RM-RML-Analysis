#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/dsp/audio_hal.hpp"
#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/card_handler_events.hpp"
#include "presonus/noaa/router.hpp"
#include "presonus/surface_panel/OutputPin.hpp"
#include "presonus/uc/firmware_update_listener.hpp"
#include <cassert>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <execinfo.h>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unistd.h>
#include <vector>
using namespace Presonus::NOAA;
using namespace presonus::noaa;
namespace {
std::vector<std::string> trace;
bool capture = false, inject = false;
void *queueLock = nullptr;
void *mainLock = nullptr, *root = nullptr, *cardObject = nullptr,
     *routerObject = nullptr;
unsigned rootDeletes = 0, cardDeletes = 0, routerDeletes = 0;
ISysexReceiver *observedCardReceiver = nullptr,
               *observedRouterReceiver = nullptr,
               *observedHandlerReceiver = nullptr;
CardHandlerEventQueue *runningQueue = nullptr;
TCardHandler *runningHandler = nullptr;
CardHandlerState *runningState = nullptr;
unsigned starvation = 0, sleeps4 = 0;
std::int64_t ticks = 0;
std::vector<int> firmwareResults;
struct Guard {
  bool old = capture;
  Guard() { capture = false; }
  ~Guard() { capture = old; }
};
template <class... A> void event(const char *name, A... args) {
  if (!capture)
    return;
  std::ostringstream s;
  s << name;
  ((s << ':' << static_cast<long long>(args)), ...);
  trace.push_back(s.str());
}
struct IO final : SpiServiceIO {
  int open(const char *, int) override { return -1; }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const SpiTransfer &) override { return -1; }
  int close(int) override { std::abort(); }
  int errorNumber() override { return ENODEV; }
  std::int64_t rawTicks() override { return ticks += 100000000; }
  void diagnostic(bool, const char *, int, bool) override {}
};
struct Pins final : presonus::surface_panel_port::InputPinIO,
                    presonus::surface_panel_port::OutputPinIO {
  std::FILE *open(const char *, const char *) override { return nullptr; }
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
  void rewind(std::FILE *f) override { assert(!f); }
  int flush(std::FILE *f) override {
    assert(!f);
    return EOF;
  }
  int get(std::FILE *f) override {
    assert(!f);
    return EOF;
  }
  int put(int, std::FILE *) override { std::abort(); }
  int error() override { return ENODEV; }
  void notify(Presonus::Panel::PinStateObserver *p, int pin,
              int value) override {
    p->pinStateChanged(pin, value);
  }
  void log(const char *) override {}
  void logSet(const char *, int, int) override {}
};
struct Response final : presonus::dice::ResponseServices {
  std::int64_t clockRawTicks() override { return ticks += 100000000; }
  void pumpIdle(bool) override {}
  void sleepMilliseconds(std::uint32_t) override {}
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {}
};
struct Hal final : Presonus::Dsp::IAudioHAL {
  void resetBoard(int, int) override {}
  void enableDACs(bool, bool, int) override { std::abort(); }
  void enableAMP(bool) override { std::abort(); }
  void suspendControlSurfaces(bool) override { std::abort(); }
};
struct Listener final : Presonus::UC::IFirmwareUpdateListener {
  std::vector<std::string> observed;
  void onProgress(const char *message, float) override {
    observed.emplace_back(message ? message : "<null>");
  }
};
void output() {
  std::cout << "{\"trace\":[";
  for (unsigned i = 0; i < trace.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << '"' << trace[i] << '"';
  }
  std::cout << "],\"root_deletes\":" << rootDeletes
            << ",\"card_deletes\":" << cardDeletes
            << ",\"router_deletes\":" << routerDeletes
            << ",\"firmware_results\":[";
  for (unsigned i = 0; i < firmwareResults.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << firmwareResults[i];
  }
  std::cout << "]}\n";
}
} // namespace
// Reject host I/O before any object construction or static initialization.
extern "C" int __wrap_open(const char *, int, ...) {
  errno = ENODEV;
  return -1;
}
extern "C" std::FILE *__wrap_fopen(const char *, const char *) {
  errno = ENODEV;
  return nullptr;
}
extern "C" int __wrap_socket(int, int, int) { std::abort(); }
extern "C" int __wrap_ioctl(int, unsigned long, ...) { std::abort(); }
extern "C" int __wrap_close(int) { std::abort(); }
extern "C" ssize_t __wrap_read(int, void *, std::size_t) { std::abort(); }
extern "C" ssize_t __wrap_write(int, const void *, std::size_t) {
  std::abort();
}
extern "C" int __wrap_tcgetattr(int, void *) { std::abort(); }
extern "C" int __wrap_tcsetattr(int, int, const void *) { std::abort(); }
extern "C" int __wrap_tcflush(int, int) { std::abort(); }
extern "C" void __wrap__ZN4Core8Platform13CurrentThread5sleepEj(unsigned n) {
  if (n == 4 && runningQueue) {
    event("sleep", n);
    ++sleeps4;
    if (sleeps4 == starvation) {
      Guard guard;
      runningQueue->consumeOne(*runningHandler, *runningState);
    }
  }
}
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *p) {
  __real__ZN4Core8Platform9PosixLock4lockEv(p);
  if (p == mainLock)
    event("main.lock");
  if (p == queueLock)
    event("queue.lock");
}
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *p) {
  if (p == mainLock)
    event("main.unlock");
  if (p == queueLock)
    event("queue.unlock");
  __real__ZN4Core8Platform9PosixLock6unlockEv(p);
}
extern "C" void
__real__ZN8Presonus4NOAA12TCardHandler11purgeEventsEv(TCardHandler *);
extern "C" void
__wrap__ZN8Presonus4NOAA12TCardHandler11purgeEventsEv(TCardHandler *p) {
  event("purge");
  if (inject)
    throw std::runtime_error("injected purge boundary exception");
  Guard g;
  __real__ZN8Presonus4NOAA12TCardHandler11purgeEventsEv(p);
}
extern "C" void *__real__Znwm(std::size_t);
static unsigned failAllocation = 0;
static std::string failPhase;
extern "C" void *__wrap__Znwm(std::size_t n) {
  if ((failPhase == "card_alloc" && n == sizeof(TCard)) ||
      (failPhase == "router_alloc" && n == sizeof(TCardRouter)) ||
      (failAllocation && --failAllocation == 0))
    throw std::bad_alloc();
  return __real__Znwm(n);
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == root) {
    ++rootDeletes;
    event("delete.handler");
  }
  if (p == cardObject) {
    ++cardDeletes;
    event("delete.card");
  }
  if (p == routerObject) {
    ++routerDeletes;
    event("delete.router");
  }
  __real__ZdlPv(p);
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == root) {
    ++rootDeletes;
    event("delete.handler");
  }
  if (p == cardObject) {
    ++cardDeletes;
    event("delete.card");
  }
  if (p == routerObject) {
    ++routerDeletes;
    event("delete.router");
  }
  __real__ZdlPvm(p, n);
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouter15setGEQToFWRouteEhh(
    TCardRouter *p, unsigned char a0, unsigned char a1);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouter15setGEQToFWRouteEhh(
    TCardRouter *p, unsigned char a0, unsigned char a1) {
  event("setGEQToFWRoute", a0, a1);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter15setGEQToFWRouteEhh(p, a0, a1);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter24setMixerCustomInputRouteEhhii(
    TCardRouter *p, unsigned char a0, unsigned char a1, int a2, int a3);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter24setMixerCustomInputRouteEhhii(
    TCardRouter *p, unsigned char a0, unsigned char a1, int a2, int a3) {
  event("setMixerCustomInputRoute", a0, a1, a2, a3);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter24setMixerCustomInputRouteEhhii(
      p, a0, a1, a2, a3);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter32setAvbTapeRxToDigitalReturnRouteEiib(
    TCardRouter *p, int a0, int a1, bool a2);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter32setAvbTapeRxToDigitalReturnRouteEiib(
    TCardRouter *p, int a0, int a1, bool a2) {
  event("setAvbTapeRxToDigitalReturnRoute", a0, a1, a2);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter32setAvbTapeRxToDigitalReturnRouteEiib(
      p, a0, a1, a2);
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouter18setDspToAvbTxRouteEiiiib(
    TCardRouter *p, int a0, int a1, int a2, int a3, bool a4);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouter18setDspToAvbTxRouteEiiiib(
    TCardRouter *p, int a0, int a1, int a2, int a3, bool a4) {
  event("setDspToAvbTxRoute", a0, a1, a2, a3, a4);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter18setDspToAvbTxRouteEiiiib(p, a0, a1, a2,
                                                                  a3, a4);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter20setDspToDanteTxRouteEiiii(TCardRouter *p,
                                                                 int a0, int a1,
                                                                 int a2,
                                                                 int a3);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter20setDspToDanteTxRouteEiiii(TCardRouter *p,
                                                                 int a0, int a1,
                                                                 int a2,
                                                                 int a3) {
  event("setDspToDanteTxRoute", a0, a1, a2, a3);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter20setDspToDanteTxRouteEiiii(p, a0, a1,
                                                                   a2, a3);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter20setLinkBusToAvbRouteEiiii(TCardRouter *p,
                                                                 int a0, int a1,
                                                                 int a2,
                                                                 int a3);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter20setLinkBusToAvbRouteEiiii(TCardRouter *p,
                                                                 int a0, int a1,
                                                                 int a2,
                                                                 int a3) {
  event("setLinkBusToAvbRoute", a0, a1, a2, a3);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter20setLinkBusToAvbRouteEiiii(p, a0, a1,
                                                                   a2, a3);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter23setAvbStageBoxMainRouteEiii(
    TCardRouter *p, int a0, int a1, int a2);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter23setAvbStageBoxMainRouteEiii(
    TCardRouter *p, int a0, int a1, int a2) {
  event("setAvbStageBoxMainRoute", a0, a1, a2);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter23setAvbStageBoxMainRouteEiii(p, a0, a1,
                                                                     a2);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter22setMixerMuteInputRouteEhi(
    TCardRouter *p, unsigned char a0, int a1);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter22setMixerMuteInputRouteEhi(
    TCardRouter *p, unsigned char a0, int a1) {
  event("setMixerMuteInputRoute", a0, a1);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter22setMixerMuteInputRouteEhi(p, a0, a1);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter20setAvbToLinkBusRouteEiiii(TCardRouter *p,
                                                                 int a0, int a1,
                                                                 int a2,
                                                                 int a3);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter20setAvbToLinkBusRouteEiiii(TCardRouter *p,
                                                                 int a0, int a1,
                                                                 int a2,
                                                                 int a3) {
  event("setAvbToLinkBusRoute", a0, a1, a2, a3);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter20setAvbToLinkBusRouteEiiii(p, a0, a1,
                                                                   a2, a3);
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouter13setAVS48RouteEhhih(
    TCardRouter *p, unsigned char a0, unsigned char a1, int a2,
    unsigned char a3);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouter13setAVS48RouteEhhih(
    TCardRouter *p, unsigned char a0, unsigned char a1, int a2,
    unsigned char a3) {
  event("setAVS48Route", a0, a1, a2, a3);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter13setAVS48RouteEhhih(p, a0, a1, a2, a3);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter26setAvbToSlaveFwRecordRouteEiiib(
    TCardRouter *p, int a0, int a1, int a2, bool a3);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter26setAvbToSlaveFwRecordRouteEiiib(
    TCardRouter *p, int a0, int a1, int a2, bool a3) {
  event("setAvbToSlaveFwRecordRoute", a0, a1, a2, a3);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter26setAvbToSlaveFwRecordRouteEiiib(
      p, a0, a1, a2, a3);
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouter19setGEQTDMSlotInsertEjjj(
    TCardRouter *p, unsigned int a0, unsigned int a1, unsigned int a2);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouter19setGEQTDMSlotInsertEjjj(
    TCardRouter *p, unsigned int a0, unsigned int a1, unsigned int a2) {
  event("setGEQTDMSlotInsert", a0, a1, a2);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter19setGEQTDMSlotInsertEjjj(p, a0, a1, a2);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter24setAvbTapeLRToAvbTxRouteEiii(
    TCardRouter *p, int a0, int a1, int a2);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter24setAvbTapeLRToAvbTxRouteEiii(
    TCardRouter *p, int a0, int a1, int a2) {
  event("setAvbTapeLRToAvbTxRoute", a0, a1, a2);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter24setAvbTapeLRToAvbTxRouteEiii(p, a0, a1,
                                                                      a2);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter23setTalkbackToAvbTxRouteEiii(
    TCardRouter *p, int a0, int a1, int a2);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter23setTalkbackToAvbTxRouteEiii(
    TCardRouter *p, int a0, int a1, int a2) {
  event("setTalkbackToAvbTxRoute", a0, a1, a2);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter23setTalkbackToAvbTxRouteEiii(p, a0, a1,
                                                                     a2);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter22setInputToDanteTxRouteEiiiii(
    TCardRouter *p, int a0, int a1, int a2, int a3, int a4);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter22setInputToDanteTxRouteEiiiii(
    TCardRouter *p, int a0, int a1, int a2, int a3, int a4) {
  event("setInputToDanteTxRoute", a0, a1, a2, a3, a4);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter22setInputToDanteTxRouteEiiiii(
      p, a0, a1, a2, a3, a4);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter20setInputToAvbTxRouteEiiii(TCardRouter *p,
                                                                 int a0, int a1,
                                                                 int a2,
                                                                 int a3);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter20setInputToAvbTxRouteEiiii(TCardRouter *p,
                                                                 int a0, int a1,
                                                                 int a2,
                                                                 int a3) {
  event("setInputToAvbTxRoute", a0, a1, a2, a3);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter20setInputToAvbTxRouteEiiii(p, a0, a1,
                                                                   a2, a3);
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouter19set2TrackInputRouteEhh(
    TCardRouter *p, unsigned char a0, unsigned char a1);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouter19set2TrackInputRouteEhh(
    TCardRouter *p, unsigned char a0, unsigned char a1) {
  event("set2TrackInputRoute", a0, a1);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter19set2TrackInputRouteEhh(p, a0, a1);
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter22setAvbToDacBypassRouteEiiiib(
    TCardRouter *p, int a0, int a1, int a2, int a3, bool a4);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter22setAvbToDacBypassRouteEiiiib(
    TCardRouter *p, int a0, int a1, int a2, int a3, bool a4) {
  event("setAvbToDacBypassRoute", a0, a1, a2, a3, a4);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter22setAvbToDacBypassRouteEiiiib(
      p, a0, a1, a2, a3, a4);
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouter13setSPDIFRouteEhhi(
    TCardRouter *p, unsigned char a0, unsigned char a1, int a2);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouter13setSPDIFRouteEhhi(
    TCardRouter *p, unsigned char a0, unsigned char a1, int a2) {
  event("setSPDIFRoute", a0, a1, a2);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter13setSPDIFRouteEhhi(p, a0, a1, a2);
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouter18setMixerInputRouteEhib(
    TCardRouter *p, unsigned char a0, int a1, bool a2);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouter18setMixerInputRouteEhib(
    TCardRouter *p, unsigned char a0, int a1, bool a2) {
  event("setMixerInputRoute", a0, a1, a2);
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter18setMixerInputRouteEhib(p, a0, a1, a2);
}
extern "C" unsigned char
__real__ZN8Presonus4NOAA5TCard14setClockSourceEi(TCard *p, int a);
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA5TCard14setClockSourceEi(TCard *p, int a) {
  event("setClockSource", a);
  Guard g;
  auto result = __real__ZN8Presonus4NOAA5TCard14setClockSourceEi(p, a);
  return result;
}
extern "C" unsigned char
__real__ZN8Presonus4NOAA5TCard18programSerialResetEv(TCard *p);
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA5TCard18programSerialResetEv(TCard *p) {
  event("programSerialReset");
  Guard g;
  auto result = __real__ZN8Presonus4NOAA5TCard18programSerialResetEv(p);
  return result;
}
extern "C" std::int32_t
__real__ZN8Presonus4NOAA5TCard13eraseFirmwareEv(TCard *p);
extern "C" std::int32_t
__wrap__ZN8Presonus4NOAA5TCard13eraseFirmwareEv(TCard *p) {
  event("eraseFirmware");
  Guard g;
  auto result = __real__ZN8Presonus4NOAA5TCard13eraseFirmwareEv(p);
  firmwareResults.push_back(result);
  return result;
}
extern "C" std::int32_t
__real__ZN8Presonus4NOAA5TCard14updateFirmwareEPNS_2UC23IFirmwareUpdateListenerEi(
    TCard *p, Presonus::UC::IFirmwareUpdateListener *l, int mode);
extern "C" std::int32_t
__wrap__ZN8Presonus4NOAA5TCard14updateFirmwareEPNS_2UC23IFirmwareUpdateListenerEi(
    TCard *p, Presonus::UC::IFirmwareUpdateListener *l, int mode) {
  event("updateFirmware", mode);
  Guard g;
  auto result =
      __real__ZN8Presonus4NOAA5TCard14updateFirmwareEPNS_2UC23IFirmwareUpdateListenerEi(
          p, l, mode);
  firmwareResults.push_back(result);
  return result;
}
extern "C" int __real__ZN8Presonus4NOAA5TCard4openERKNS0_17NOAASetupPropertyE(
    TCard *p, const NOAASetupProperty &s);
extern "C" int __wrap__ZN8Presonus4NOAA5TCard4openERKNS0_17NOAASetupPropertyE(
    TCard *p, const NOAASetupProperty &s) {
  event("card.open");
  Guard g;
  auto result =
      __real__ZN8Presonus4NOAA5TCard4openERKNS0_17NOAASetupPropertyE(p, s);
  return result;
}
extern "C" bool
__real__ZN8Presonus4NOAA11TCardRouter4openERKNS0_17NOAASetupPropertyE(
    TCardRouter *p, const NOAASetupProperty &s);
extern "C" bool
__wrap__ZN8Presonus4NOAA11TCardRouter4openERKNS0_17NOAASetupPropertyE(
    TCardRouter *p, const NOAASetupProperty &s) {
  event("router.open");
  Guard g;
  auto result =
      __real__ZN8Presonus4NOAA11TCardRouter4openERKNS0_17NOAASetupPropertyE(p,
                                                                            s);
  return result;
}
extern "C" bool __real__ZN8Presonus4NOAA5TCard5startEb(TCard *p, bool force);
extern "C" bool __wrap__ZN8Presonus4NOAA5TCard5startEb(TCard *p, bool force) {
  event("card.start", force);
  Guard g;
  auto result = __real__ZN8Presonus4NOAA5TCard5startEb(p, force);
  return result;
}
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter11routeScriptEPKc(TCardRouter *p,
                                                       const char *s);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter11routeScriptEPKc(TCardRouter *p,
                                                       const char *s) {
  event("routeScript");
  Guard g;
  __real__ZN8Presonus4NOAA11TCardRouter11routeScriptEPKc(p, s);
}
extern "C" void
__real__ZN4Core8Platform11PosixThread5startERKNS0_10ThreadInfoE(void *, void *);
extern "C" void
__wrap__ZN4Core8Platform11PosixThread5startERKNS0_10ThreadInfoE(void *p,
                                                                void *e) {
  event("thread.start");
  Guard g;
  __real__ZN4Core8Platform11PosixThread5startERKNS0_10ThreadInfoE(p, e);
}
extern "C" void __real__ZN8Presonus4NOAA5TCardC1Ev(TCard *p);
extern "C" void __wrap__ZN8Presonus4NOAA5TCardC1Ev(TCard *p) {
  event("card.ctor");
  cardObject = p;
  observedCardReceiver = static_cast<ISysexReceiver *>(p);
  if (failPhase == "card_ctor")
    throw std::bad_alloc();
  __real__ZN8Presonus4NOAA5TCardC1Ev(p);
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouterC1Ev(TCardRouter *p);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouterC1Ev(TCardRouter *p) {
  event("router.ctor");
  routerObject = p;
  observedRouterReceiver = static_cast<ISysexReceiver *>(p);
  if (failPhase == "router_ctor")
    throw std::bad_alloc();
  __real__ZN8Presonus4NOAA11TCardRouterC1Ev(p);
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouterD1Ev(TCardRouter *p);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouterD1Ev(TCardRouter *p) {
  event("router.D1");
  __real__ZN8Presonus4NOAA11TCardRouterD1Ev(p);
}
const char *receiverKind(ISysexReceiver *p) {
  // Exact compiler-adjusted base identities from typed real constructor
  // wrappers. No RTTI lookup or classification of unknown registrations.
  if (p == observedCardReceiver && p != nullptr)
    return "card";
  if (p == observedRouterReceiver && p != nullptr)
    return "router";
  if (p == observedHandlerReceiver && p != nullptr)
    return "handler";
  std::abort();
}
extern "C" void
__real__ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *, ISysexReceiver *);
extern "C" void
__wrap__ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *spi, ISysexReceiver *p) {
  if (capture)
    trace.emplace_back(std::string("register.") + receiverKind(p));
  if (failPhase == "register" && std::string(receiverKind(p)) == "handler")
    throw std::bad_alloc();
  __real__ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE(
      spi, p);
}
extern "C" void
__real__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *, ISysexReceiver *);
extern "C" void
__wrap__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *spi, ISysexReceiver *p) {
  if (capture)
    trace.emplace_back(std::string("unregister.") + receiverKind(p));
  __real__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE(
      spi, p);
}
extern "C" void __real__ZN4Core8Platform11PosixThread11setPriorityEi(void *,
                                                                     int);
extern "C" void __wrap__ZN4Core8Platform11PosixThread11setPriorityEi(void *p,
                                                                     int n) {
  event("priority", n);
  __real__ZN4Core8Platform11PosixThread11setPriorityEi(p, n);
}
extern "C" void
__real__ZN8Presonus4NOAA12TCardHandler19setPropertyDeferredERKN4Core8PropertyE(
    TCardHandler *, const Core::Property &);
int expectedPayloadCount = -1;
std::array<unsigned char, 504> expectedPayloadBytes{};
extern "C" void
__wrap__ZN8Presonus4NOAA12TCardHandler19setPropertyDeferredERKN4Core8PropertyE(
    TCardHandler *h, const Core::Property &p) {
  if (expectedPayloadCount >= 0) {
    auto *payload = h->portableHandlerState().payload;
    assert(payload && payload->property == &p && p.type == 123 &&
           payload->count == static_cast<unsigned>(expectedPayloadCount));
    for (unsigned i = 0; i < payload->count; ++i)
      assert(payload->bytes[i] == expectedPayloadBytes[i]);
    expectedPayloadCount = -1;
  }
  __real__ZN8Presonus4NOAA12TCardHandler19setPropertyDeferredERKN4Core8PropertyE(
      h, p);
}
struct SingletonAccess : TCardHandler {
  static TCardHandler *get() { return theInstance; }
  static void set(TCardHandler *p) { theInstance = p; }
};
extern "C" void _ZN8Presonus4NOAA12TCardHandlerC1Ev(TCardHandler *);
extern "C" void _ZN8Presonus4NOAA12TCardHandlerC2Ev(TCardHandler *);
extern "C" void _ZN8Presonus4NOAA12TCardHandlerD1Ev(TCardHandler *);
extern "C" void _ZN8Presonus4NOAA12TCardHandlerD2Ev(TCardHandler *);
int main(int argc, char **argv) {
  assert(argc >= 2);
  static IO io;
  static Pins pins;
  setSpiServiceConstructionIO(&io);
  presonus::surface_panel_port::setInputPinConstructionIO(&pins);
  presonus::surface_panel_port::setOutputPinConstructionIO(&pins);
  const std::string kind(argv[1]);
  if (kind == "lifecycle") {
    assert(argc == 5);
    const std::string ctor(argv[2]), dtor(argv[3]);
    bool equal = std::stoi(argv[4]) != 0;
    // Invoke each actual compiled variant; D1/D2 retain allocated root storage.
    void *storage = ::operator new(sizeof(TCardHandler));
    auto *h = static_cast<TCardHandler *>(storage);
    observedHandlerReceiver = static_cast<ISysexReceiver *>(h);
    auto *other = reinterpret_cast<TCardHandler *>(std::uintptr_t(0x1000));
    SingletonAccess::set(equal ? h : other);
    capture = true;
    if (ctor == "C1")
      _ZN8Presonus4NOAA12TCardHandlerC1Ev(h);
    else
      _ZN8Presonus4NOAA12TCardHandlerC2Ev(h);
    assert(SingletonAccess::get() == (equal ? h : other));
    assert(!h->portableHandlerState().stopRequested.load());
    assert(h->portableHandlerState().observedByte65 == 0 &&
           h->portableHandlerState().observedByte66 == 0);
    assert(h->portableHandlerState().eventQueue &&
           h->portableHandlerState().eventQueue->pending() == 0);
    assert(observedCardReceiver ==
           static_cast<ISysexReceiver *>(&h->portableHandlerState().card));
    assert(observedRouterReceiver ==
           static_cast<ISysexReceiver *>(h->portableHandlerState().router));
    root = h;
    cardObject = &h->portableHandlerState().card;
    routerObject = h->portableHandlerState().router;
    auto &receivers = SpiServiceAccess::state(TCardSPI::instance()).receivers;
    assert(receivers.contains(static_cast<ISysexReceiver *>(h)));
    assert(receivers.contains(
        static_cast<ISysexReceiver *>(static_cast<TCard *>(cardObject))));
    assert(receivers.contains(static_cast<ISysexReceiver *>(
        static_cast<TCardRouter *>(routerObject))));
    if (dtor == "D0")
      delete h;
    else if (dtor == "D1")
      _ZN8Presonus4NOAA12TCardHandlerD1Ev(h);
    else
      _ZN8Presonus4NOAA12TCardHandlerD2Ev(h);
    capture = false;
    assert(rootDeletes == (dtor == "D0") && cardDeletes == 1 &&
           routerDeletes == 1 && receivers.count() == 0);
    assert(SingletonAccess::get() == (equal ? nullptr : other));
    SingletonAccess::set(nullptr);
    if (dtor != "D0") {
      root = nullptr;
      ::operator delete(storage);
    }
    root = cardObject = routerObject = nullptr;
    output();
    return 0;
  }
  if (kind == "ctor-failure") {
    assert(argc == 5);
    const std::string phase(argv[2]), ctor(argv[3]);
    bool equal = std::stoi(argv[4]) != 0;
    auto &receivers = SpiServiceAccess::state(TCardSPI::instance()).receivers;
    assert(receivers.count() == 0);
    void *storage = ::operator new(sizeof(TCardHandler));
    auto *h = static_cast<TCardHandler *>(storage);
    observedHandlerReceiver = static_cast<ISysexReceiver *>(h);
    auto *other = reinterpret_cast<TCardHandler *>(std::uintptr_t(0x1000));
    SingletonAccess::set(equal ? h : other);
    failPhase = phase;
    capture = true;
    bool rejected = false;
    try {
      if (ctor == "C1")
        _ZN8Presonus4NOAA12TCardHandlerC1Ev(h);
      else
        _ZN8Presonus4NOAA12TCardHandlerC2Ev(h);
    } catch (const std::bad_alloc &) {
      rejected = true;
    }
    capture = false;
    failPhase.clear();
    assert(rejected && rootDeletes == 0);
    assert(SingletonAccess::get() == (equal ? nullptr : other));
    SingletonAccess::set(nullptr);
    const unsigned retained =
        phase == "register"                                 ? 2
        : phase == "router_alloc" || phase == "router_ctor" ? 1
                                                            : 0;
    assert(receivers.count() == static_cast<int>(retained));
    // Observe native application retention before explicit test-owned cleanup.
    std::cout << "{\"retained\":" << retained << ",\"trace\":[";
    for (unsigned i = 0; i < trace.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << '"' << trace[i] << '"';
    }
    std::cout << "]}\n";
    while (receivers.count()) {
      auto *receiver = receivers[0];
      if (receiver == observedCardReceiver && cardObject != nullptr) {
        auto *card = static_cast<TCard *>(cardObject);
        assert(static_cast<ISysexReceiver *>(card) == receiver);
        delete card;
        observedCardReceiver = nullptr;
      } else if (receiver == observedRouterReceiver &&
                 routerObject != nullptr) {
        auto *router = static_cast<TCardRouter *>(routerObject);
        assert(static_cast<ISysexReceiver *>(router) == receiver);
        delete router;
        observedRouterReceiver = nullptr;
      } else {
        std::abort();
      }
    }
    root = cardObject = routerObject = nullptr;
    ::operator delete(storage);
    return 0;
  }

  Response response;
  CardState cs{};
  cs.expectedSerial = 5;
  cs.observedWord14 = 1;
  cs.observedWord20 = cs.observedWord28 = 1;
  Hal hal;
  cs.audioHal = &hal;
  cs.opaque5c.value = &hal;
  Presonus::ResourceLibrary resources;
  const unsigned char image[] = {1, 2, 3, 4};
  for (const char *name : {"NIMH_ARM", "NIMH_FPGA", "ESA_ARM", "ESA_FPGA"})
    resources.addFirmware(name, 1, image, 4, false);
  resources.addFirmware("NOAA_S800ARM", 1, image, 4, false);
  resources.addFirmware("NOAA_S800FPGA", 1, image, 4, false);
  cs.resources = &resources;
  TCard card(cardSetupTag, cs, response, io);
  RouterState rs{};
  rs.slotTables = &rm13731GambitRouterSlots();
  TCardRouter router(rs, response, io, rm13731LinkAddressRouterLookup());
  CardHandlerState state{card};
  state.router = &router;
  CardHandlerEventQueue queue(1, 1, 1);
  queue.bind(state);
  TCardHandler handler(cardHandlerSetupTag, state, response);
  runningQueue = &queue;
  runningHandler = &handler;
  runningState = &state;
  mainLock = &queue.mainLock();
  queueLock = &queue.queueLock();
  if (kind == "property") {
    assert(argc == 11);
    unsigned id = std::stoul(argv[2]);
    cs.observedWord14 = std::stoul(argv[3]);
    int size = std::stoi(argv[4]);
    Core::Property property(id, size);
    ImmediatePropertyProjection projection{&property};
    for (unsigned i = 0; i < 5; ++i)
      projection.words[i] = std::stoul(argv[5 + i]);
    state.immediate = &projection;
    Listener listener;
    state.updateProperty = &property;
    state.updateListener = &listener;
    state.updateMode = static_cast<int>(projection.words[1]);
    if (id == 0x75647461)
      cs.observedWord20 = 0;
    NOAASetupProperty setup("/offline/no-device", {&hal},
                            rm13731GambitRouterSlots(), 7, {nullptr});
    state.setup = &setup;
    state.scriptProperty = &property;
    state.script = "/offline/no-script";
    // Real Thread::start is executed but the independent stop publication makes
    // the consumer exit before touching application/provider state.
    state.stopRequested.store(true);
    capture = true;
    inject = std::stoi(argv[10]) != 0;
    try {
      handler.setProperty(id == NOAASetupProperty::kID
                              ? static_cast<const Core::Property &>(setup)
                              : property);
    } catch (const std::exception &) {
      event("exception");
    }
    capture = false;
    if (id == NOAASetupProperty::kID)
      handler.join(3000);
    output();
    return 0;
  }
  if (kind == "enqueue") {
    assert(argc == 5);
    int size = std::stoi(argv[2]);
    unsigned starve = std::stoul(argv[4]);
    Core::Property property(123, size);
    CardHandlerPayloadProjection payload{&property};
    payload.count = size - 8;
    std::string bytes(argv[3]);
    assert(bytes.size() == static_cast<unsigned>(size) * 2);
    for (unsigned i = 0; i < payload.count; ++i)
      payload.bytes[i] = std::stoul(bytes.substr(16 + i * 2, 2), nullptr, 16);
    state.payload = &payload;
    if (starve) {
      handler.setProperty(property);
      starvation = starve;
    }
    capture = true;
    handler.setProperty(property);
    capture = false;
    assert(queue.pending() == 1 && sleeps4 == starve);
    output();
    return 0;
  }
  if (kind == "fifo") {
    const auto *previous = state.payload;
    for (int size : {16, 17, 33}) {
      Core::Property property(123, size);
      CardHandlerPayloadProjection payload{&property};
      payload.count = size - 8;
      payload.bytes.fill(static_cast<unsigned char>(size));
      state.payload = &payload;
      handler.setProperty(property);
      state.payload = previous;
    }
    assert(queue.pending() == 3 && queue.queuedNodes() == 3);
    for (int size : {16, 17, 33}) {
      expectedPayloadCount = size - 8;
      expectedPayloadBytes.fill(static_cast<unsigned char>(size));
      queue.consumeOne(handler, state);
      assert(expectedPayloadCount == -1 && state.payload == previous);
    }
    assert(queue.pending() == 0 && queue.queuedNodes() == 0);
    std::cout << "{\"fifo_cases\":3}\n";
    return 0;
  }
  if (kind == "queue") {
    // Real finite-pool starvation followed by an independently scheduled
    // consume.
    int size = std::stoi(argv[2]);
    Core::Property property(123, size);
    ImmediatePropertyProjection projection{&property, {1, 2, 3, 4, 5}};
    CardHandlerPayloadProjection payload{&property};
    payload.count = size - 8;
    assert(argc == 4);
    std::string nativeBytes(argv[3]);
    assert(nativeBytes.size() == static_cast<unsigned>(size) * 2);
    for (unsigned i = 0; i < payload.count; ++i)
      payload.bytes[i] =
          std::stoul(nativeBytes.substr(16 + 2 * i, 2), nullptr, 16);
    state.payload = &payload;
    state.immediate = &projection;
    handler.setProperty(property);
    assert(queue.pending() == 1);
    if (size > 8) {
      expectedPayloadCount = payload.count;
      expectedPayloadBytes = payload.bytes;
      payload.bytes[0] ^= 0xff;
    }
    queue.consumeOne(handler, state);
    assert(expectedPayloadCount == -1 && state.payload == &payload);
    handler.setProperty(property);
    assert(queue.pending() == 1);
    starvation = 2;
    handler.setProperty(property);
    assert(sleeps4 == 2 && queue.pending() == 1);
    queue.consumeOne(handler, state);
    assert(queue.pending() == 0);
    assert(state.immediate == &projection);
    for (int bad : {-1, 0, 7, 513}) {
      Core::Property invalid(123, bad);
      bool rejected = false;
      try {
        handler.setProperty(invalid);
      } catch (const std::invalid_argument &) {
        rejected = true;
      }
      assert(rejected);
    }
    handler.setProperty(property);
    state.stopRequested.store(true);
    handler.setProperty(property);
    assert(queue.pending() == 1);
    queue.consumeOne(handler, state);
    // Allocation failure after pop must restore slot and count, then retry
    // works.
    failAllocation = 1;
    bool rejected = false;
    try {
      handler.setProperty(property);
    } catch (const std::bad_alloc &) {
      rejected = true;
    }
    failAllocation = 0;
    assert(rejected && queue.pending() == 0);
    handler.setProperty(property);
    queue.consumeOne(handler, state);
    assert(queue.pending() == 0);
    std::cout << "{\"queue_cases\":10,\"sleeps4\":" << sleeps4 << "}\n";
    return 0;
  }
  std::abort();
}

extern "C" [[noreturn]] void __wrap_abort() {
  void *frames[32];
  int n = backtrace(frames, 32);
  backtrace_symbols_fd(frames, n, 2);
  _Exit(86);
}
