#include "presonus/mixer/GEQLinkHandler.hpp"

#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string_view>
#include <vector>

using namespace Core::Portable;
using Presonus::Mixer::GEQLinkHandler;

namespace {
bool trace{};
const Parameter *destination{}, *source{}, *distinct{};
const Parameter *stringSource{};
IParamObserver *registered{};
const Parameter *registeredParameter{};

const char *identity(const Parameter *pointer) {
  if (pointer == stringSource)
    return "string";
  if (pointer == destination)
    return "destination";
  if (pointer == source)
    return "source";
  assert(pointer == distinct);
  return "distinct";
}

std::uint32_t bits(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
float word(std::uint32_t value) {
  float result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}

struct Probe : NumericParam {
  using NumericParam::NumericParam;
  bool overrideValue{};
  float forced{};
  int writes{};
  ParamValue getValue() const override {
    const auto result = overrideValue ? forced : NumericParam::getValue();
    if (trace)
      std::cout << "get " << identity(this) << ' ' << bits(result) << '\n';
    return result;
  }
  void setValue(ParamValue value, bool edit) override {
    ++writes;
    if (trace)
      std::cout << "set " << identity(this) << ' ' << bits(value) << ' ' << edit
                << '\n';
    NumericParam::setValue(value, edit);
  }
};

struct Recorder : ParamObserverBase {
  std::vector<int> messages;
  void paramChanged(Parameter *, int message) override {
    messages.push_back(message);
  }
};

struct Derived : GEQLinkHandler {
  using GEQLinkHandler::GEQLinkHandler;
};

ParamInfo info() {
  ParamInfo result{};
  result.type = ParamInfo::kFloat;
  result.minValue = -1;
  result.maxValue = 1;
  return result;
}
} // namespace

extern "C" void
realComponent(Component *,
              const char *) asm("__real__ZN4Core8Portable9ComponentC2EPKc");
extern "C" void
wrapComponent(Component *,
              const char *) asm("__wrap__ZN4Core8Portable9ComponentC2EPKc");
extern "C" void wrapComponent(Component *self, const char *name) {
  if (trace) {
    assert(name && !*name);
    std::cout << "component\n";
  }
  realComponent(self, name);
}

extern "C" void realAdd(Parameter *, IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE");
extern "C" void wrapAdd(Parameter *, IParamObserver *) asm(
    "__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE");
extern "C" void wrapAdd(Parameter *parameter, IParamObserver *observer) {
  if (trace) {
    const char *label = identity(parameter);
    std::cout << "add " << label << '\n';
    registeredParameter = parameter;
    registered = observer;
  }
  realAdd(parameter, observer);
}

extern "C" void realRemove(Parameter *, IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(Parameter *, IParamObserver *) asm(
    "__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(Parameter *parameter, IParamObserver *observer) {
  if (trace) {
    assert(observer == registered);
    std::cout << "remove " << identity(parameter) << '\n';
  }
  realRemove(parameter, observer);
}

template <class Handler>
void constructorCase(Probe *dest, Parameter *src, Probe &numeric,
                     StringParam &string) {
  trace = true;
  Handler handler(dest, src);
  trace = false;
  assert(!*handler.getName());
  assert(registeredParameter == src);
  if (src)
    assert(registered == static_cast<IParamObserver *>(&handler));
  const auto before = dest ? dest->writes : 0;
  if (src == &string)
    string.fromString("updated", false);
  else if (src == &numeric)
    numeric.NumericParam::setValue(0.5f);
  else if (src)
    dest->NumericParam::setValue(0.5f);
  if (dest)
    assert(dest->writes == before + (src ? 1 : 0));
  if (src)
    handler.paramChanged(src, Parameter::kDestroyed);
}

void callbackCase(Probe *dest, Probe &destProbe, Probe &src, Probe &other,
                  std::string_view passed, int message, std::uint32_t input) {
  GEQLinkHandler handler(dest, &src);
  registered = static_cast<IParamObserver *>(&handler);
  Probe *arg = passed == "source"        ? &src
               : passed == "distinct"    ? &other
               : passed == "destination" ? &destProbe
                                         : nullptr;
  if (arg) {
    if (arg == dest) {
      arg->NumericParam::setValue(word(input));
    } else {
      arg->overrideValue = true;
      arg->forced = word(input);
    }
  }
  const auto spec = info();
  NumericParam reference(spec);
  Recorder actualEdit, actualChange, referenceEdit, referenceChange;
  if (dest) {
    reference.setValue(dest->NumericParam::getValue());
    dest->setController(&actualEdit);
    dest->addObserver(&actualChange);
    reference.setController(&referenceEdit);
    reference.addObserver(&referenceChange);
  }
  trace = true;
  handler.paramChanged(arg, message);
  trace = false;
  if (dest) {
    if (message == Parameter::kChanged)
      reference.setValue(word(input), true);
    assert(bits(reference.getValue()) == bits(dest->NumericParam::getValue()));
    assert(actualEdit.messages == referenceEdit.messages &&
           actualChange.messages == referenceChange.messages);
    dest->removeObserver(&actualChange);
    dest->setController(nullptr);
    reference.removeObserver(&referenceChange);
    reference.setController(nullptr);
  }
  src.overrideValue = false;
  if (dest && message == Parameter::kDestroyed && arg != &src) {
    const int before = dest->writes;
    src.NumericParam::setValue(0.25f);
    assert(dest->writes == before + 1);
  }
  handler.paramChanged(&src, Parameter::kDestroyed);
  if (dest) {
    const int before = dest->writes;
    src.NumericParam::setValue(0.75f);
    assert(dest->writes == before);
  }
}

int main(int argc, char **argv) {
  assert(argc >= 4);
  const std::string_view variant = argv[1], destName = argv[2], arg = argv[3];
  const auto spec = info();
  Probe destProbe(spec), src(spec), other(spec);
  StringParam string(spec);
  destination = &destProbe;
  stringSource = &string;
  source = arg == "string" ? static_cast<Parameter *>(&string) : &src;
  distinct = &other;
  Probe *dest = destName == "destination" ? &destProbe : nullptr;
  if (variant == "callback") {
    assert(argc == 6);
    callbackCase(dest, destProbe, src, other, arg, std::atoi(argv[4]),
                 std::strtoul(argv[5], nullptr, 10));
    return 0;
  }
  assert(argc == 4);
  auto *input = arg == "source"        ? static_cast<Parameter *>(&src)
                : arg == "string"      ? static_cast<Parameter *>(&string)
                : arg == "destination" ? dest
                                       : nullptr;
  if (variant == "C1")
    constructorCase<GEQLinkHandler>(dest, input, src, string);
  else {
    assert(variant == "C2");
    constructorCase<Derived>(dest, input, src, string);
  }
}
