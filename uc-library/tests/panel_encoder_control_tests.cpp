#include "presonus/panel/encoder_control.hpp"
#include "presonus/panel/key_input_provider.hpp"
#include "presonus/panel/param_edit_handler.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
#include <string>
#include <vector>
using E = Presonus::Panel::EncoderControl;
using A = presonus::panel::ControlAccess;
using X = presonus::panel::EncoderControlAccess;
extern "C" void ec1(E *, int) asm("_ZN8Presonus5Panel14EncoderControlC1Ei");
extern "C" void ec2(E *, int) asm("_ZN8Presonus5Panel14EncoderControlC2Ei");
extern "C" void ed1(E *) asm("_ZN8Presonus5Panel14EncoderControlD1Ev");
extern "C" void ed0(E *) asm("_ZN8Presonus5Panel14EncoderControlD0Ev");
namespace {
bool capturing = false;
std::vector<std::string> events;
void *tracked = nullptr;
int frees = 0;
void emit(const std::string &event) {
  if (capturing)
    events.push_back(event);
}
int signedBits(std::uint32_t raw) {
  int value;
  std::memcpy(&value, &raw, 4);
  return value;
}
class Delegate final : public Presonus::Panel::IKeyInputDelegate {
public:
  bool value = false;
  bool altKeyPressed() const override {
    emit("alt");
    return value;
  }
};
class ActualParam final : public Core::Portable::NumericParam {
  mutable bool inside = false;

public:
  using NumericParam::NumericParam;
  bool isEnabled() const override {
    if (!inside)
      emit("enabled");
    return NumericParam::isEnabled();
  }
  int getPrecision() const override {
    if (!inside)
      emit("precision");
    return NumericParam::getPrecision();
  }
  void resetValue(bool edit) override {
    if (!inside)
      emit("reset:" + std::to_string(int(edit)));
    inside = true;
    NumericParam::resetValue(edit);
    inside = false;
  }
  void increment(int n) override {
    if (!inside)
      emit("increment:" + std::to_string(n));
    inside = true;
    NumericParam::increment(n);
    inside = false;
  }
  void decrement(int n) override {
    if (!inside)
      emit("decrement:" + std::to_string(n));
    inside = true;
    NumericParam::decrement(n);
    inside = false;
  }
};
std::array<std::uint32_t, 5> state(E &v) {
  return {static_cast<std::uint32_t>(A::lastLevel(v)),
          unsigned(v.getParameter() != nullptr),
          static_cast<std::uint32_t>(A::tag(v)),
          static_cast<std::uint32_t>(X::threshold(v)), X::accumulator(v)};
}
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == tracked) {
    ++frees;
    emit("X");
  }
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == tracked) {
    ++frees;
    emit("X");
  }
  __real__ZdlPvm(p, n);
}
extern "C" void
__real__ZN8Presonus5Panel7ControlD2Ev(Presonus::Panel::Control *);
extern "C" void
__wrap__ZN8Presonus5Panel7ControlD2Ev(Presonus::Panel::Control *control) {
  if (control == tracked)
    emit("D");
  __real__ZN8Presonus5Panel7ControlD2Ev(control);
}
extern "C" void
__real__ZN8Presonus5Panel16ParamEditHandler15handleParamEditEPN4Core8Portable9ParameterE(
    Presonus::Panel::ParamEditHandler *, Core::Portable::Parameter *);
extern "C" void
__wrap__ZN8Presonus5Panel16ParamEditHandler15handleParamEditEPN4Core8Portable9ParameterE(
    Presonus::Panel::ParamEditHandler *handler,
    Core::Portable::Parameter *parameter) {
  emit("edit");
  __real__ZN8Presonus5Panel16ParamEditHandler15handleParamEditEPN4Core8Portable9ParameterE(
      handler, parameter);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::string op;
  std::uint32_t arg, threshold, total;
  int present, enabled, alt, precision, delegatePresent;
  unsigned checked = 0, actualDeletes = 0;
  while (input >> op >> arg >> present >> enabled >> alt >> precision >>
         threshold >> total >> delegatePresent) {
    std::array<std::uint32_t, 5> expected;
    for (auto &n : expected)
      input >> n;
    unsigned count;
    input >> count;
    std::vector<std::string> wanted(count);
    for (auto &v : wanted)
      input >> v;
    int expectedCast, expectedAlt;
    input >> expectedCast >> expectedAlt;
    capturing = false;
    Core::Portable::ParamInfo info{};
    info.type = precision == 0 ? Core::Portable::ParamInfo::kInt
                               : Core::Portable::ParamInfo::kFloat;
    info.minValue = 0;
    info.maxValue = 1;
    info.defaultValue = precision == 0 ? 0.f : .5f;
    info.deltaValue = precision ? 1.f / static_cast<float>(precision) : 0;
    ActualParam parameter(info);
    parameter.enable(enabled != 0);
    if (parameter.getPrecision() != precision) {
      std::cerr << "precision mismatch " << precision << ' '
                << parameter.getPrecision() << '\n';
      return 4;
    }
    // Real source semantics, not a substitute provider: huge floating-step
    // requests run at saturation so actual NumericParam returns immediately.
    // Original app oracle captures the request, not Core's stored value. A
    // zero-delta integer NumericParam avoids the actual float zero-step loop.
    for (const auto &event : wanted) {
      const bool increment = event.rfind("increment:", 0) == 0;
      const bool decrement = event.rfind("decrement:", 0) == 0;
      if ((increment || decrement) &&
          std::stoll(event.substr(event.find(':') + 1)) > 4096)
        parameter.setNormalized(increment ? 1.f : 0.f, false);
    }
    Delegate delegate;
    delegate.value = alt != 0;
    auto &provider = Presonus::Panel::KeyInputProvider::instance();
    presonus::panel::KeyInputProviderAccess::bind(
        provider, delegatePresent ? &delegate : nullptr);
    void *memory = ::operator new(sizeof(E));
    auto *control = static_cast<E *>(memory);
    if (op == "C2")
      ec2(control, signedBits(arg));
    else
      ec1(control, op == "C1" ? signedBits(arg) : 7);
    if (op != "C1" && op != "C2") {
      A::parameter(*control) = present ? &parameter : nullptr;
      X::threshold(*control) = signedBits(threshold);
      X::accumulator(*control) = total;
    }
    auto actual = state(*control);
    tracked = control;
    frees = 0;
    events.clear();
    capturing = true;
    int cast = -1, altResult = -1;
    if (op == "D1")
      ed1(control);
    else if (op == "D0")
      ed0(control);
    else {
      if (op == "K")
        cast = control->castTo(signedBits(arg)) == control;
      else if (op == "R")
        control->receiveValue(signedBits(arg));
      else if (op == "A")
        altResult = provider.altKeyPressed();
      actual = state(*control);
    }
    capturing = false;
    if (actual != expected || events != wanted || cast != expectedCast ||
        altResult != expectedAlt || frees != (op == "D0" ? 1 : 0)) {
      std::cerr << "case " << checked << ' ' << op << " mismatch\n";
      for (auto n : actual)
        std::cerr << n << ' ';
      std::cerr << " events ";
      for (auto &v : events)
        std::cerr << v << ' ';
      std::cerr << " wanted ";
      for (auto &v : wanted)
        std::cerr << v << ' ';
      std::cerr << '\n';
      return 3;
    }
    actualDeletes += frees;
    tracked = nullptr;
    presonus::panel::KeyInputProviderAccess::bind(provider, nullptr);
    auto &edit = A::paramEdits();
    presonus::panel::ParamEditHandlerAccess::edits(edit).removeAll();
    presonus::panel::ParamEditHandlerAccess::blockers(edit).removeAll();
    if (op == "D1")
      ::operator delete(memory);
    else if (op != "D0")
      delete control;
    ++checked;
  }
  if (checked != 1035 || actualDeletes != 1)
    std::abort();
  std::cout << "{\"passed\":true,\"cases\":" << checked
            << ",\"actual_D0_deletes\":" << actualDeletes << "}\n";
}
