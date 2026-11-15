#include "core/portable/corepersistence.h"
#include "presonus/AltMemoryFilter.hpp"
#include "presonus/LinkableComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
using namespace Core::Portable;
namespace {
constexpr unsigned Alt = 0x1000090, Src = 0x1002000, Nested = 0x1003000;
std::string hex(const std::string &s) {
  const char *digits = "0123456789abcdef";
  std::string out;
  for (unsigned char c : s) {
    out += digits[c >> 4];
    out += digits[c & 15];
  }
  return out;
}
std::string snapshot(const Attributes &a) {
  std::ostringstream s;
  s << '{';
  for (int i = 0; i < a.countAttributes(); ++i) {
    const auto *v = a.getAttribute(i);
    s << a.getAttributeName(i) << ':' << v->getType() << '=';
    if (v->getType() == Attribute::kAttributes)
      s << snapshot(*v->getAttributes());
    else if (v->getType() == Attribute::kString)
      s << v->getString();
    else
      s << v->getInt();
    s << ';';
  }
  s << '}';
  return s.str();
}
void seed(Attributes &a, int n) {
  a.removeAll();
  if (n) {
    a.set("i", n == 1 ? 17 : -23);
    if (n > 1) {
      a.set("text", "borrowed UTF8 \xd0\xb0");
      a.makeAttributes("nested")->set("value", 99);
    }
  }
}
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
struct Cancel final : IStorageCancelHook {
  bool value = false;
  bool shouldCancelStorage() const override { return value; }
};
} // namespace
int main(int argc, char **argv) {
  bool provider = argc > 1 && std::string(argv[1]) == "--provider";
  int method, pattern, altPattern, ignore, cancel;
  if (!(std::cin >> method >> pattern >> altPattern >> ignore >> cancel))
    return 2;
  Presonus::linkable_port::State state;
  Boundary boundary;
  Presonus::LinkableComponent object(state, boundary);
  Attributes source(AttributeAllocator::getDefault()),
      output(AttributeAllocator::getDefault());
  seed(state.alternate, altPattern);
  static const ParamInfo recallInfo =
      PARAM_INT(1, "recall", -100, 100, 0, nullptr, nullptr, 0,
                PARAM_STORABLE | PARAM_USERFLAG1);
  static const ParamInfo excludedInfo = PARAM_INT(
      2, "excluded", -100, 100, 0, nullptr, nullptr, 0, PARAM_STORABLE);
  state.component.addParameters(&recallInfo, 1);
  state.component.addParameters(&excludedInfo, 1);
  auto *recall = state.component.getParameterByTag(1);
  auto *excluded = state.component.getParameterByTag(2);
  recall->setValue(11 + pattern);
  excluded->setValue(42);
  state.alternate.removeAll();
  if (altPattern) {
    state.alternate.set("recall", altPattern == 1 ? 17 : -23);
    state.alternate.set("excluded", 99);
  }
  state.partner = ignore ? &object : nullptr;
  state.slave = cancel;
  AltMemoryFilter filter;
  if (method == 5) {
    if (pattern)
      seed(*source.makeAttributes("altmem"), pattern);
  } else
    seed(source, pattern);
  AttributesBuilder builder(output);
  OutputStorage storage(builder);
  InputStorage input(source);
  Cancel hook;
  hook.value = cancel;
  storage.setCancelHook(&hook);
  storage.setMode(ignore ? "ignoreAltMemory" : "preset");
  input.setMode(ignore ? "ignoreAltMemory" : "preset");
  bool saved = true;
  if (!provider) {
    if (method == 3)
      object.toggleAltMemory();
    else if (method == 2)
      object.copyToAltMemory(source);
    else if (method == 4)
      saved = object.save(storage);
    else if (method == 5)
      object.loadAltMemory(input);
    else
      return 3;
    std::cout << hex(snapshot(state.alternate)) << ' ' << hex(snapshot(output))
              << ' ' << saved << ' ' << recall->getValue() << ' '
              << excluded->getValue() << '\n';
    return 0;
  }
  // Independent source-provider RPC: no Linkable target is invoked in this
  // mode.
  std::map<unsigned, Attributes *> attrs{{Alt, &state.alternate},
                                         {Src, &source}};
  std::map<unsigned, std::unique_ptr<AttributePoolSuspender>> suspenders;
  std::map<unsigned, std::unique_ptr<Attributes>> copies;
  std::unique_ptr<AttributesBuilder> alternateBuilder;
  std::string op;
  while (std::cin >> op) {
    unsigned a = 0, b = 0;
    int value = 0;
    if (op == "LOCK")
      Presonus::linkable_port::State::alternateLock.lock();
    else if (op == "UNLOCK")
      Presonus::linkable_port::State::alternateLock.unlock();
    else if (op == "SUSPEND") {
      std::cin >> a;
      suspenders[a] = std::make_unique<AttributePoolSuspender>();
    } else if (op == "RESUME") {
      std::cin >> a;
      suspenders.erase(a);
    } else if (op == "CLEAR") {
      std::cin >> a;
      attrs.at(a)->removeAll();
    } else if (op == "COPY") {
      std::cin >> a >> b;
      attrs.at(a)->copyFrom(*attrs.at(b));
    } else if (op == "REAL") {
      std::cin >> a;
      attrs.at(a)->makeReal();
    } else if (op == "GET") {
      auto *nested = source.getAttributes("altmem");
      if (nested)
        attrs[Nested] = nested;
      value = nested ? Nested : 0;
    } else if (op == "COUNT") {
      std::cin >> a;
      value = attrs.at(a)->countAttributes();
    } else if (op == "COPYCTOR") {
      std::cin >> a >> b;
      copies[a] = std::make_unique<Attributes>(*attrs.at(b));
      attrs[a] = copies[a].get();
      value = attrs.at(a)->countAttributes();
    } else if (op == "DTOR") {
      std::cin >> a;
      attrs.erase(a);
      copies.erase(a);
    } else if (op == "BUILDER") {
      alternateBuilder = std::make_unique<AttributesBuilder>(state.alternate);
    } else if (op == "DROPBUILDER") {
      alternateBuilder.reset();
    } else if (op == "LOAD") {
      std::cin >> a;
      InputStorage restored(*attrs.at(a), &filter);
      value = state.component.load(restored);
    } else if (op == "SAVE") {
      OutputStorage target(*alternateBuilder, &filter);
      saved = state.component.save(target);
      value = saved;
    } else if (op == "WRITER") {
    } else if (op == "WRITE") {
      std::cin >> a;
      AttributesWriter writer(builder);
      writer.writeObject("altmem", *attrs.at(a), Attribute::kShareID);
    } else if (op == "REPORT") {
      std::cout << hex(snapshot(state.alternate)) << ' '
                << hex(snapshot(output)) << ' ' << saved << ' '
                << recall->getValue() << ' ' << excluded->getValue()
                << std::endl;
      continue;
    } else
      return 4;
    std::cout << value << std::endl;
  }
}
