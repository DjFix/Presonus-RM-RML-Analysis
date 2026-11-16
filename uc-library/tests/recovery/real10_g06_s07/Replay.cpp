#include "presonus/mixer/FXComponent.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
struct App : presonus::mixer_fx::AppBoundary {
  void setControllerDirty() override { std::abort(); }
  std::uint32_t getTypeNumber() override { std::abort(); }
  void updateTypeName() override { std::abort(); }
  void handleTypeChange(bool) override { std::abort(); }
};
struct Filter : Core::Portable::IStorageFilter {
  void *castTo(int) override { return nullptr; }
  bool shouldLoad(int, const char *, void *) const override { return true; }
  bool shouldSave(int, const char *, void *) const override { return true; }
};
struct Boundary : Presonus::dspcomponent_port::Boundary {
  const Core::Portable::Attributes *attrs{};
  const Core::Portable::IStorageFilter *filter{};
  presonus::mixer_fx::LoadState *state{};
  bool observed = false;
  int result = 0;
  int count(Presonus::Dsp::IController &) override { std::abort(); }
  float value(Presonus::Dsp::IController &, int) override { std::abort(); }
  void set(Presonus::Dsp::IController &, int, float) override { std::abort(); }
  unsigned flags(Presonus::Dsp::IController &) override { std::abort(); }
  void acknowledge(Presonus::Dsp::IController &) override { std::abort(); }
  bool readout(Presonus::Dsp::IController &, int) override { std::abort(); }
  int load(const Core::Portable::InputStorage &s) override {
    observed = state->loading && &s.getAttributes() == attrs &&
               s.getFilter() == filter &&
               std::strcmp(s.getMode(), "ignoreAltMemory") == 0 &&
               !s.getCancelHook() && !s.getLock() && !s.getParentAttributes();
    return result;
  }
  void idle() override { std::abort(); }
  void changed(Core::Portable::Parameter *, int) override { std::abort(); }
};
int main() {
  int fil, res;
  std::uint32_t bits[3];
  while (std::cin >> fil >> res >> bits[0] >> bits[1] >> bits[2]) {
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = -1000;
    info.maxValue = 1000;
    Core::Portable::NumericParam a(info), b(info), c(info);
    Core::Portable::NumericParam *ps[] = {&a, &b, &c};
    for (int i = 0; i < 3; ++i) {
      float f;
      std::memcpy(&f, &bits[i], 4);
      ps[i]->setValue(f, false);
    }
    Core::Portable::Component owner;
    App app;
    Presonus::DspComponent dsp("fx", nullptr);
    Boundary boundary;
    dsp.bind(boundary);
    presonus::mixer_fx::LoadState load{dsp, a, b, c};
    presonus::mixer_fx::State state{owner, a, b, app};
    state.load = &load;
    Presonus::Mixer::FXComponent fx(state);
    Core::Portable::Attributes attrs(
        Core::Portable::AttributeAllocator::getDefault());
    Filter filter;
    Core::Portable::InputStorage input(attrs, fil ? &filter : nullptr);
    input.setMode("original");
    boundary.attrs = &attrs;
    boundary.filter = input.getFilter();
    boundary.state = &load;
    boundary.result = res;
    bool result = fx.load(input);
    std::cout << "ROW " << result << ' ' << boundary.observed << ' '
              << load.loading << ' '
              << (std::strcmp(input.getMode(), "original") == 0) << '\n';
  }
}
