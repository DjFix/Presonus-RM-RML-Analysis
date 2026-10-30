#include "presonus/panel/input_gpio_control.hpp"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
using E = Presonus::Panel::InputGPIOControl;
using A = presonus::panel::ControlAccess;
namespace {
bool capture = false, inside = false;
std::vector<std::string> events;
void emit(std::string s) {
  if (capture && !inside)
    events.push_back(s);
}
float floating(unsigned x) {
  float f;
  std::memcpy(&f, &x, 4);
  return f;
}
unsigned bits(float f) {
  unsigned x;
  std::memcpy(&x, &f, 4);
  return x;
}
class Parameter : public Core::Portable::NumericParam {
public:
  using NumericParam::NumericParam;
  void beginEdit() override {
    emit("begin");
    inside = true;
    NumericParam::beginEdit();
    inside = false;
  }
  void endEdit() override {
    emit("end");
    inside = true;
    NumericParam::endEdit();
    inside = false;
  }
  float getValue() const override {
    emit("get");
    return NumericParam::getValue();
  }
  float getMax() const override {
    emit("max");
    return NumericParam::getMax();
  }
  void setValue(float v, bool edit) override {
    emit("set:" + std::to_string(bits(v)) + ":" + std::to_string(edit));
    inside = true;
    NumericParam::setValue(v, edit);
    inside = false;
  }
};
// Genuine libc files inside the project fixture directory. Only paths are
// redirected; actual InputPin setup/read/debounce and stdio operations run.
class IO : public presonus::surface_panel_port::InputPinIO {
  std::string directory;

public:
  explicit IO(std::string p) : directory(std::move(p)) {}
  FILE *open(const char *path, const char *mode) override {
    const char *name = std::strstr(path, "/export")      ? "export"
                       : std::strstr(path, "/direction") ? "direction"
                                                         : "value";
    return std::fopen((directory + "/" + name).c_str(), mode);
  }
  int printPin(FILE *f, const char *fmt, int p) override {
    return std::fprintf(f, fmt, p);
  }
  int close(FILE *f) override { return std::fclose(f); }
  void formatPath(char *out, std::size_t n, const char *fmt, int p) override {
    std::snprintf(out, n, fmt, p);
  }
  std::size_t write(const void *d, std::size_t a, std::size_t n,
                    FILE *f) override {
    return std::fwrite(d, a, n, f);
  }
  int buffering(FILE *f, char *b, int m, std::size_t n) override {
    return std::setvbuf(f, b, m, n);
  }
  void rewind(FILE *f) override { std::rewind(f); }
  int flush(FILE *f) override { return std::fflush(f); }
  int get(FILE *f) override { return std::fgetc(f); }
  void notify(Presonus::Panel::PinStateObserver *o, int p, int v) override {
    o->pinStateChanged(p, v);
  }
  void log(const char *) override {}
};
} // namespace
extern "C" void
realRemove(Core::Portable::Parameter *, Core::Portable::IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void
wrapRemove(Core::Portable::Parameter *p, Core::Portable::IParamObserver *o) asm(
    "__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(Core::Portable::Parameter *p,
                           Core::Portable::IParamObserver *o) {
  emit("remove");
  realRemove(p, o);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::string path = argv[1];
  std::string directory = path.substr(0, path.find_last_of('/'));
  {
    std::ofstream value(directory + "/value");
    value << '0';
  }
  IO io(directory);
  auto *previous = presonus::surface_panel_port::setInputPinConstructionIO(&io);
  std::ifstream input(path);
  std::string op;
  unsigned present, complete, inverse, value, kind, maximum, arg, message,
      expectedPresent, expectedValue, count, checked = 0;
  while (input >> op >> present >> complete >> inverse >> value >> kind >>
         maximum >> arg >> message >> expectedPresent >> expectedValue >>
         count) {
    std::vector<std::string> wanted(count);
    for (auto &s : wanted)
      input >> s;
    Core::Portable::ParamInfo info{};
    info.type = kind;
    info.minValue = 0;
    info.maxValue = floating(maximum);
    info.deltaValue = 1;
    Parameter parameter(info);
    parameter.NumericParam::setValue(floating(value), false);
    E control(7, 99, complete, inverse);
    A::parameter(control) = present ? &parameter : nullptr;
    events.clear();
    capture = true;
    if (op == "D")
      control.switchDown();
    else if (op == "U")
      control.switchUp();
    else if (op == "S")
      control.pinStateChanged(99, static_cast<int>(arg));
    else if (op == "H") {
      Presonus::Panel::PinStateObserver &observer = control;
      observer.pinStateChanged(99, static_cast<int>(arg));
    } else
      control.paramChanged(&parameter, static_cast<int>(message));
    capture = false;
    unsigned actual = bits(parameter.NumericParam::getValue());
    if (events != wanted ||
        bool(A::parameter(control)) != bool(expectedPresent) ||
        actual != expectedValue) {
      std::cerr << "case " << checked << ' ' << op << " kind " << kind
                << " value " << value << " got " << actual << " wanted "
                << expectedValue << " events ";
      for (auto &s : events)
        std::cerr << s << ' ';
      std::cerr << " wanted ";
      for (auto &s : wanted)
        std::cerr << s << ' ';
      std::cerr << '\n';
      return 3;
    }
    A::parameter(control) = nullptr;
    ++checked;
  }
  presonus::surface_panel_port::setInputPinConstructionIO(previous);
  std::cout << "{\"passed\":true,\"cases\":" << checked << "}\n";
}
