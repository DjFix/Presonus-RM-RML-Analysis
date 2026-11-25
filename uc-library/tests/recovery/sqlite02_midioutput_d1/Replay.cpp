#include "presonus/surface/UCMidiOutputAdapter.hpp"

#include <algorithm>
#include <array>
#include <iostream>
#include <new>
#include <type_traits>

namespace {
using Presonus::IMidiSink;
using Presonus::MackieControlModel;
using Presonus::Surface::MackieFaderUnitBinding;
using Presonus::Surface::UCMidiOutputAdapter;

class Endpoint final : public IMidiSink {
public:
  void sendMidiMessage(const unsigned char *data, unsigned length,
                       unsigned port) override {
    ++messages;
    if (length == midi.size())
      std::copy_n(data, length, midi.begin());
    lastPort = port;
  }

  std::array<unsigned char, 3> midi{};
  unsigned lastPort = 0;
  unsigned messages = 0;
};

#ifdef MIDI_OUTPUT_BASE_VARIANT
class TestedAdapter : public UCMidiOutputAdapter {
public:
  TestedAdapter() : UCMidiOutputAdapter() {}
  explicit TestedAdapter(IMidiSink &sink) : UCMidiOutputAdapter(sink) {}
  ~TestedAdapter() override {}
};
#else
using TestedAdapter = UCMidiOutputAdapter;
#endif

static_assert(!std::is_copy_constructible_v<TestedAdapter>);

MackieControlModel *captured = nullptr;
unsigned resetCalls = 0;
bool unexpectedArguments = false;
} // namespace

extern "C" void
__real__ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi(
    MackieControlModel *, IMidiSink *, int);

extern "C" void
__wrap__ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi(
    MackieControlModel *model, IMidiSink *sink, int index) {
  if (captured) {
    ++resetCalls;
    unexpectedArguments |= (model != captured || sink || index != 0);
  }
  __real__ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi(
      model, sink, index);
}

namespace {
bool checkBorrowedEndpoint() {
  Endpoint endpoint;
  TestedAdapter configured(endpoint);
  const std::array<unsigned char, 3> bytes{0x90, 1, 2};
  configured.sendMidiMessage(bytes.data(), bytes.size(), 9);
  return configured.portableEndpoint() == &endpoint &&
         configured.portableFaderUnit() == nullptr && endpoint.messages == 1 &&
         endpoint.midi == bytes && endpoint.lastPort == 9;
}

#ifdef MIDI_OUTPUT_DESTRUCTOR
bool exercise(bool endpointBound, bool faderBound) {
  Endpoint endpoint;
  MackieControlModel model;
  MackieFaderUnitBinding fader(model);
  alignas(TestedAdapter) unsigned char buffer[sizeof(TestedAdapter)];
  auto *adapter = endpointBound ? new (buffer) TestedAdapter(endpoint)
                                : new (buffer) TestedAdapter;
  if (faderBound)
    adapter->setFaderUnit(&fader, -9);
  if (model.applicationMidiSink != (faderBound ? adapter : nullptr))
    return false;
  captured = &model;
  resetCalls = 0;
  unexpectedArguments = false;
  adapter->TestedAdapter::~TestedAdapter();
  captured = nullptr;
  const bool endpointUntouched = endpoint.messages == 0;
  std::cout << resetCalls << ' ' << (model.applicationMidiSink == nullptr)
            << ' ' << endpointUntouched << '\n';
  return !unexpectedArguments && endpointUntouched &&
         model.applicationMidiSink == nullptr;
}
#else
bool exercise(bool, bool) {
  TestedAdapter unbound;
  MackieControlModel model;
  captured = &model;
  resetCalls = 0;
  {
    TestedAdapter original;
    if (original.portableEndpoint() || original.portableFaderUnit())
      return false;
  }
  captured = nullptr;
  std::cout << (unbound.portableEndpoint() != nullptr) << ' '
            << (unbound.portableFaderUnit() != nullptr) << ' ' << resetCalls
            << '\n';
  return resetCalls == 0;
}
#endif
} // namespace

int main() {
  if (!checkBorrowedEndpoint())
    return 1;
  bool endpoint, fader;
  while (std::cin >> endpoint >> fader)
    if (!exercise(endpoint, fader))
      return 2;
  return std::cin.eof() ? 0 : 3;
}
