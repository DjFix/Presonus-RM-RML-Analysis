#include "presonus/mixer/setup_property_applications.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/panel/uart_message.hpp"
#include <cstring>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
struct Trace {
  unsigned gets = 0;
  unsigned writes = 0;
  std::string message;
  std::string wire;
};

class Port final : public Presonus::Panel::ProtocolComm {
public:
  explicit Port(Trace &trace) : trace_(trace) {}
  int writeMsg(Uart_Msg_Type &message) override {
    if (trace_.gets != 1 || trace_.writes != 0)
      throw std::logic_error("unexpected transport order");
    ++trace_.writes;
    trace_.message.assign(message.bytes.begin(), message.bytes.end());
    return ProtocolComm::writeMsg(message);
  }

private:
  int open(const char *) override { return 0; }
  void close() override {}
  int enableHISpeed(bool) override { return 0; }
  int read(char *, int) override { return 0; }
  int write(const char *bytes, int count) override {
    trace_.wire.append(bytes, count);
    return count;
  }
  Trace &trace_;
};

class Registrar final : public Presonus::Panel::PanelRegistrar {
public:
  Registrar(presonus::panel_binding::PanelRegistrarPortState &state,
            Trace &trace)
      : PanelRegistrar(state), trace_(trace) {}
  Presonus::IPanelPort *getPort() const override {
    if (trace_.writes != 0)
      throw std::logic_error("getPort after transport write");
    ++trace_.gets;
    return PanelRegistrar::getPort();
  }

private:
  Trace &trace_;
};

class Rack final : public Presonus::Mixer::RackMixerApplication {
public:
  explicit Rack(const presonus::mixer::SetupContext &setup)
      : RackMixerApplication(presonus::mixer::setupContextTag, setup) {}

private:
  bool isNetworkClientReady() const override { return false; }
  Presonus::UC::ClientRootComponent *
  createClientComponent(const Presonus::UC::NetworkItem &) override {
    return nullptr;
  }
  void releaseClientComponent(Presonus::UC::ClientRootComponent *) override {}
  Presonus::NOAA::NOAASetupProperty getNOAASetupProperty() const override {
    throw std::logic_error("out-of-domain setup query");
  }
};

void printHex(const std::string &bytes) {
  std::cout << std::hex << std::setfill('0');
  for (unsigned char byte : bytes)
    std::cout << std::setw(2) << static_cast<unsigned>(byte);
  std::cout << std::dec;
}
} // namespace

int main() {
  std::uint32_t bits;
  int present, titleKind;
  while (std::cin >> bits >> present >> titleKind) {
    Trace trace;
    Port port(trace);
    presonus::panel_binding::PanelRegistrarPortState state;
    state.port = present ? &port : nullptr;
    Registrar registrar(state, trace);
    const presonus::mixer::SetupContext setup({nullptr}, {nullptr});
    Rack rack(setup);
    rack.bindProgressRegistrar(registrar);
    float progress;
    static_assert(sizeof(progress) == sizeof(bits));
    std::memcpy(&progress, &bits, sizeof(progress));
    const char text[] = "synthetic progress title";
    const char *titles[] = {nullptr, text, text + 10};
    static_cast<Presonus::UC::IFirmwareUpdateListener &>(rack).onProgress(
        titles[titleKind], progress);
    std::cout << trace.gets << ' ' << trace.writes << ' ';
    printHex(trace.message);
    std::cout << ':';
    printHex(trace.wire);
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
