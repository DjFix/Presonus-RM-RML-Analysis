#include "presonus/surface/PresetsPageComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <type_traits>

namespace {
using namespace presonus::surface;
using Presonus::Surface::PresetsPageComponent;
static_assert(
    std::is_same_v<decltype(&PresetsPageComponent::getTargetUrl),
                   void (PresetsPageComponent::*)(Core::CStringBuffer<256> &)>);

class UnexpectedDependencies final : public PresetsPageDependencies {
public:
  bool handlerAvailable() override { std::abort(); }
  int count(int) override { std::abort(); }
  const PresetEntry *preset(int, int) override { std::abort(); }
  void reload(int) override { std::abort(); }
  void defaultName(int, Core::CString128 &) override { std::abort(); }
  void categoryName(int, Core::CString128 &) override { std::abort(); }
  const char *emptyMarker() override { std::abort(); }
  void baseShow(bool) override { std::abort(); }
  bool visible() override { std::abort(); }
  void connect(const char *, Core::Portable::Parameter *) override {
    std::abort();
  }
  void recallOptions(Core::CString256 &) override { std::abort(); }
  void recall(const PresetEntry *, int, const Core::CString256 &) override {
    std::abort();
  }
  void remove(const PresetEntry *, int) override { std::abort(); }
  void store() override { std::abort(); }
  void startTextInput(Core::Portable::Parameter *, const char *) override {
    std::abort();
  }
};
} // namespace

int main() {
  int selected;
  if (!(std::cin >> selected))
    return 2;
  Core::Portable::Component parameters("parameters");
  PresetsPageState state{0, 1, 0, selected, false, parameters};
  UnexpectedDependencies dependencies;
  PresetsPageComponent component(state, dependencies);
  Core::CStringBuffer<256> url;
  for (int index = 0; index < url.getSize(); ++index) {
    unsigned value;
    if (!(std::cin >> value) || value > 127)
      return 2;
    url.getBuffer()[index] = static_cast<char>(value);
  }
  component.getTargetUrl(url);
  std::cout << state.selected;
  for (int index = 0; index < url.getSize(); ++index)
    std::cout << ' ' << static_cast<unsigned char>(url.getBuffer()[index]) + 0;
  std::cout << '\n';
}
