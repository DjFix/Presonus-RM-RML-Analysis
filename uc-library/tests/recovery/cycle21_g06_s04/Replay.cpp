#include "presonus/surface/UCMidiOutputAdapter.hpp"

#include <array>
#include <iostream>

namespace {
Presonus::MackieControlModel *modelBase;

class Endpoint final : public Presonus::IMidiSink {
public:
  void sendMidiMessage(const unsigned char *, unsigned, unsigned) override {}
};
} // namespace

extern "C" void
__real__ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi(
    Presonus::MackieControlModel *, Presonus::IMidiSink *, int);
extern "C" void
__wrap__ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi(
    Presonus::MackieControlModel *model, Presonus::IMidiSink *sink, int index) {
  std::cout << (model - modelBase + 1) << ' ' << bool(sink) << ' ' << index
            << ' ';
  __real__ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi(
      model, sink, index);
}

int main() {
  Presonus::MackieControlModel models[2];
  modelBase = models;
  Presonus::Surface::MackieFaderUnitBinding first(models[0]), second(models[1]);
  std::array<Presonus::IFaderUnit *, 3> faders{nullptr, &first, &second};
  Endpoint endpoint;
  Presonus::Surface::UCMidiOutputAdapter adapter(endpoint);
  unsigned next;
  int index;
  while (std::cin >> next >> index) {
    if (next >= faders.size())
      return 1;
    adapter.setFaderUnit(faders[next], index);
    unsigned active = adapter.portableFaderUnit() == &first    ? 1
                      : adapter.portableFaderUnit() == &second ? 2
                                                               : 0;
    std::cout << active;
    for (const auto &model : models)
      std::cout << ' ' << (model.applicationMidiSink == &adapter);
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
