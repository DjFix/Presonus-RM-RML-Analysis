#include "presonus/LinkableComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <string_view>

using namespace Core::Portable;
namespace {
struct Boundary final : Presonus::linkable_port::Boundary {
  Presonus::LinkableComponent *query(Presonus::LinkableComponent &,
                                     std::uint32_t) override {
    std::abort();
  }
  void remove(Presonus::LinkableComponent &) override { std::abort(); }
  void set(Presonus::LinkableComponent &, Presonus::LinkableComponent &,
           bool) override {
    std::abort();
  }
  void master(Presonus::LinkableComponent &,
              Presonus::LinkableComponent &) override {
    std::abort();
  }
};
struct EditCounter final : IParamObserver {
  void *castTo(int) override { return nullptr; }
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kEdit)
      ++count;
  }
  int count = 0;
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view mode(argv[1]);
  const bool edit = std::string_view(argv[2]) == "1";
  static const ParamInfo floatInfo =
      PARAM_FLOAT(1, "float", -10, 10, 0, 0, nullptr, nullptr, 0, 0);
  static const ParamInfo stringInfo = PARAM_STRING(2, "text", 0);
  static const ParamInfo colorInfo = PARAM_COLOR(3, "color", 0);
  Boundary boundary;
  EditCounter counter;
  Presonus::linkable_port::State state;
  Presonus::LinkableComponent object(state, boundary);
  NumericParam number(floatInfo);
  NumericParam numericDestination(floatInfo);
  StringParam text(stringInfo);
  StringParam textDestination(stringInfo);
  ColorParam color(colorInfo);
  ColorParam colorDestination(colorInfo);
  number.setValue(3.25f);
  text.fromString("alpha");
  color.setColor(0xff127abc, false);
  numericDestination.setValue(-2.f);
  numericDestination.setController(&counter);
  textDestination.setController(&counter);
  colorDestination.setController(&counter);
  if (mode == "numeric") {
    object.syncParams(number, numericDestination, edit);
    std::cout << numericDestination.getValue();
  } else if (mode == "string") {
    object.syncParams(text, textDestination, edit);
    char value[256];
    textDestination.toString(value, sizeof(value));
    std::cout << value;
  } else if (mode == "color") {
    object.syncParams(color, colorDestination, edit);
    std::cout << colorDestination.getColor();
  } else if (mode == "color_mismatch") {
    object.syncParams(color, numericDestination, edit);
    std::cout << numericDestination.getValue();
  } else {
    return 2;
  }
  std::cout << ' ' << counter.count << '\n';
}
