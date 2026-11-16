#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/surface/PresetsPageComponent.hpp"
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
namespace {
struct Dependencies final : presonus::surface::PresetsPageDependencies {
  bool handlerAvailable() override { throw 1; }
  int count(int) override { throw 1; }
  const presonus::surface::PresetEntry *preset(int, int) override { throw 1; }
  void reload(int) override { throw 1; }
  void defaultName(int, Core::CString128 &) override { throw 1; }
  void categoryName(int, Core::CString128 &) override { throw 1; }
  const char *emptyMarker() override { throw 1; }
  void baseShow(bool) override { throw 1; }
  bool visible() override { throw 1; }
  void connect(const char *, Core::Portable::Parameter *) override { throw 1; }
  void recallOptions(Core::CString256 &) override { throw 1; }
  void recall(const presonus::surface::PresetEntry *, int,
              const Core::CString256 &) override {
    throw 1;
  }
  void remove(const presonus::surface::PresetEntry *, int) override { throw 1; }
  void store() override { throw 1; }
  void startTextInput(Core::Portable::Parameter *, const char *) override {
    throw 1;
  }
};

struct Observer final : Presonus::IMixerComponentObserver {
  void onSelectionChanged() override { throw 1; }
  void onObjectChanged(ObjectChangeMessage) override { throw 1; }
  void onComponentReplaced(const ReplaceArgs &) override { throw 1; }
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 5)
    return 2;
  int n = std::atoi(argv[1]), duplicate = std::atoi(argv[2]),
      capacity = std::atoi(argv[3]), nullMixer = std::atoi(argv[4]);
  Core::Portable::Component parameters;
  presonus::surface::PresetsPageState state{0, 1, 0, -1, false, parameters};
  Dependencies dependencies;
  Presonus::Surface::PresetsPageComponent page(state, dependencies);
  Presonus::MixerClientComponentBase mixer;
  Observer pageObserver, other;
  Core::Vector<Presonus::IMixerComponentObserver *> observers;
  observers.resize(capacity);
  for (int j = 0; j < n; ++j)
    observers.add(j == duplicate ? &pageObserver : &other);
  Core::Vector<presonus::surface::PresetsMixerBinding> bindings;
  bindings.add({&mixer, &observers, &pageObserver});
  state.mixerBindings = &bindings;
  page.setMixerComponent(nullMixer ? nullptr : &mixer);
  std::printf("%d %d", state.mixerComponent == &mixer, observers.count());
  for (int j = 0; j < observers.count(); ++j)
    std::printf(" %d", observers[j] == &pageObserver);
  std::puts("");
}
