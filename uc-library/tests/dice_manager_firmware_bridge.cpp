#include "presonus/dice/manager.hpp"
#include "presonus/dice/manager_programmer_services.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Programmer = Presonus::DICE::Dice3Programmer;
namespace {
void check(bool x) {
  if (!x)
    std::abort();
}
std::vector<std::string> events;
std::uint32_t openWord, resultWord;
unsigned char image[1]{};
unsigned char listenerToken{};
Programmer *instance = nullptr;
presonus::dice::SubsystemState subsystem;
int throwStage = 0;
bool smoke = false;
std::int32_t asSigned(std::uint32_t x) {
  std::int32_t v;
  std::memcpy(&v, &x, 4);
  return v;
}
class Routes final : public presonus::dice::RouteSink {
public:
  std::int32_t setRoute(const presonus::dice::RouteTuple &) override {
    std::abort();
  }
};
class Runtime final : public presonus::dice::ProgrammerServices {
public:
  std::int32_t transfer(std::int32_t,
                        const presonus::dice::ProgrammerTransfer &) override {
    std::abort();
  }
  std::int64_t clockRawTicks() override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
};
class Device final : public presonus::dice::ProgrammerDeviceServices {
public:
  std::int32_t openDevice(const char *, int) override { std::abort(); }
  std::int32_t modeIoctl(std::int32_t, std::uint32_t,
                         std::uint32_t &) override {
    std::abort();
  }
  std::int32_t closeDevice(std::int32_t) override { std::abort(); }
  std::unique_ptr<presonus::dice::ProgrammerOutputPin>
  makeOutputPin(int) override {
    std::abort();
  }
};
class Binding final : public presonus::dice::ManagerProgrammerServices {
public:
  Runtime runtime;
  Device device;
  presonus::dice::BoundManagerProgrammerServices bound{runtime, device,
                                                       subsystem};
  void prepare(Programmer &p) override {
    bound.prepare(p);
    check(p.inspectState().descriptor == -1);
  }
  void invalidateSubsystemInfo() override {
    events.push_back("{\"kind\":\"invalidate\"}");
    bound.invalidateSubsystemInfo();
  }
};
} // namespace
extern "C" void
__real__ZN8Presonus4DICE15Dice3ProgrammerC1EPNS_2UC23IFirmwareUpdateListenerEPKhj(
    Programmer *, Presonus::UC::IFirmwareUpdateListener *,
    const unsigned char *, unsigned int);
extern "C" void
__wrap__ZN8Presonus4DICE15Dice3ProgrammerC1EPNS_2UC23IFirmwareUpdateListenerEPKhj(
    Programmer *p, Presonus::UC::IFirmwareUpdateListener *listener,
    const unsigned char *data, unsigned int length) {
  instance = p;
  __real__ZN8Presonus4DICE15Dice3ProgrammerC1EPNS_2UC23IFirmwareUpdateListenerEPKhj(
      p, listener, data, length);
  auto s = p->inspectState();
  check(s.listener == listener && s.image == data && s.length == length &&
        s.descriptor == -1);
  events.push_back("{\"kind\":\"construct\",\"listener\":" +
                   std::string(listener ? "true" : "false") +
                   ",\"image\":" + (data ? "true" : "false") +
                   ",\"length\":" + std::to_string(length) + "}");
}
extern "C" void __real__ZN8Presonus4DICE15Dice3ProgrammerD1Ev(Programmer *);
extern "C" void __wrap__ZN8Presonus4DICE15Dice3ProgrammerD1Ev(Programmer *p) {
  check(p == instance);
  events.push_back("{\"kind\":\"destroy\"}");
  __real__ZN8Presonus4DICE15Dice3ProgrammerD1Ev(p);
  instance = nullptr;
}
extern "C" std::int32_t
__wrap__ZN8Presonus4DICE15Dice3Programmer4openEPKc(Programmer *p,
                                                   const char *path) {
  check(p == instance && std::string(path) == "/dev/spidev0.2");
  events.push_back("{\"kind\":\"open\",\"path\":\"/dev/spidev0.2\"}");
  if (throwStage == 1)
    throw std::runtime_error("injected open");
  return asSigned(openWord);
}
extern "C" void
__wrap__ZN8Presonus4DICE15Dice3Programmer5closeEv(Programmer *p) {
  check(p == instance);
  events.push_back("{\"kind\":\"close\"}");
  if (throwStage == 3)
    throw std::runtime_error("injected close");
}
std::int32_t operation(Programmer *p, const char *name) {
  check(p == instance);
  events.push_back(std::string("{\"kind\":\"") + name + "\"}");
  if (throwStage == 2)
    throw std::runtime_error("injected operation");
  return asSigned(resultWord);
}
extern "C" std::int32_t
__wrap__ZN8Presonus4DICE15Dice3Programmer6updateEv(Programmer *p) {
  return operation(p, "update");
}
extern "C" std::int32_t
__wrap__ZN8Presonus4DICE15Dice3Programmer8eraseAllEv(Programmer *p) {
  return operation(p, "erase");
}

int main(int argc, char **argv) {
  Routes routes;
  Binding binding;
  Presonus::DICE::Dice3Manager manager(routes);
  manager.setPortableProgrammerServices(binding);
  if (argc > 1 && std::string(argv[1]) == "--exception-smoke") {
    openWord = 1;
    for (int stage = 1; stage <= 3; ++stage) {
      events.clear();
      throwStage = stage;
      bool caught = false;
      try {
        manager.updateFirmware(nullptr, image, 0);
      } catch (const std::runtime_error &) {
        caught = true;
      }
      check(caught && instance == nullptr &&
            events.back() == "{\"kind\":\"destroy\"}");
    }
    Presonus::DICE::Dice3Manager missing(routes);
    bool caught = false;
    try {
      missing.eraseFirmware();
    } catch (const std::logic_error &) {
      caught = true;
    }
    check(caught);
    std::cout << "exception/missing-provider PASS\n";
    return 0;
  }
  std::string kind;
  std::int32_t length;
  unsigned hasListener;
  while (std::cin >> kind >> openWord >> resultWord >> length >> hasListener) {
    events.clear();
    subsystem.infoWords[0] = 0x73737373;
    auto listener = reinterpret_cast<Presonus::UC::IFirmwareUpdateListener *>(
        hasListener ? &listenerToken : nullptr);
    const auto result = kind == "update"
                            ? manager.updateFirmware(listener, image, length)
                            : manager.eraseFirmware();
    check(instance == nullptr);
    std::cout << "{\"return_word\":" << static_cast<std::uint32_t>(result)
              << ",\"events\":[";
    for (std::size_t i = 0; i < events.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << events[i];
    }
    std::cout << "],\"info_word\":" << subsystem.infoWords[0] << "}\n";
  }
}
