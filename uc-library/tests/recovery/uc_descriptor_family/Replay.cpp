#include "presonus/uc/ParamRangeElement.hpp"
#include "presonus/uc/StringElement.hpp"
#include "presonus/uc/StringListElement.hpp"
#include "presonus/uc/meta_element.hpp"
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <map>
#include <string>
#include <vector>
using namespace Presonus::UC;
static std::string hex(const char *p) {
  std::string out;
  for (auto c : std::string(p ? p : "")) {
    out += "0123456789abcdef"[(unsigned char)c >> 4];
    out += "0123456789abcdef"[(unsigned char)c & 15];
  }
  return out.empty() ? "-" : out;
}
static std::string unhex(const char *p) {
  if (std::string(p) == "-")
    return "";
  std::string out;
  for (; *p; p += 2) {
    char pair[3] = {p[0], p[1], 0};
    out += char(std::strtoul(pair, nullptr, 16));
  }
  return out;
}
static std::uint64_t bits(double d) {
  std::uint64_t n;
  std::memcpy(&n, &d, 8);
  return n;
}
struct Attrs : ElementAttributes {
  std::map<std::string, std::string> values;
  mutable std::vector<std::string> trace;
  Core::CStringPtr lookupName(Core::CStringPtr key) const override {
    trace.push_back(std::string("lookup:") + key);
    auto i = values.find(key);
    return i == values.end() ? nullptr : i->second.c_str();
  }
  void storeName(Core::CStringPtr key, Core::CStringPtr value) override {
    trace.push_back(std::string("store:") + key);
    values[key] = value ? value : "";
  }
};
static void trace(const Attrs &a) {
  for (auto &s : a.trace)
    std::cout << s << ",";
}
static void range(const ParamRangeElement &e) {
  auto &r = e.range();
  std::cout << bits(r.minimum) << " " << bits(r.maximum) << " "
            << bits(r.midpoint) << " " << bits(r.defaultValue) << " " << r.steps
            << " " << e.presence() << " " << hex(r.units.str()) << " "
            << hex(r.curve.str());
}
static unsigned destroyedChildren = 0;
struct LifetimeChild : StringElement {
  using StringElement::StringElement;
  ~LifetimeChild() override { ++destroyedChildren; }
};
static void *tracked = nullptr;
static unsigned baseCalls = 0, deletes = 0;
extern "C" void realBase(void *) asm("__real__ZN8Presonus2UC7ElementD2Ev");
extern "C" void wrapBase(void *p) asm("__wrap__ZN8Presonus2UC7ElementD2Ev");
extern "C" void wrapBase(void *p) {
  if (tracked)
    ++baseCalls;
  realBase(p);
}
extern "C" void realDelete(void *) asm("__real__ZdlPv");
extern "C" void wrapDelete(void *p) asm("__wrap__ZdlPv");
extern "C" void wrapDelete(void *p) {
  if (tracked)
    ++deletes;
  realDelete(p);
}
int main(int argc, char **argv) {
  assert(argc >= 2);
  std::string mode = argv[1];
  MetaElement metadata("descriptor", nullptr);
  if (mode == "vector") {
    const int count = std::atoi(argv[2]);
    Core::Vector<Element *> values;
    for (int i = 0; i < count; ++i)
      assert(values.add(
          reinterpret_cast<Element *>(std::uintptr_t(0x1000 + i * 16))));
    const bool result = values.resize(0);
    std::cout << result << " " << values.count() << " " << values.getCapacity();
  } else if (mode == "provider") {
    assert(argc == 5 || argc == 6);
    int capacity = std::atoi(argv[2]);
    std::string format = argv[3];
    std::string source = unhex(argv[4]);
    if (capacity == 32) {
      const std::string initial = argc == 6 ? unhex(argv[5]) : "";
      Core::CString32 text(format == "text" ? source.c_str() : initial.c_str());
      if (format == "text") {
        // Genuine pinned constructor/copy boundary; no numeric formatting.
      } else if (format == "double") {
        std::uint64_t n = std::strtoull(source.c_str(), nullptr, 10);
        double d;
        std::memcpy(&d, &n, 8);
        text.appendFormat("%lf", d);
      } else
        text.appendFormat("%d", std::atoi(source.c_str()));
      std::cout << hex(text.str());
    } else if (capacity == 64) {
      Core::CString64 text(source.c_str());
      std::cout << hex(text.str());
    } else {
      Core::CString128 text(source.c_str());
      std::cout << hex(text.str());
    }
  } else if (mode == "parse") {
    Element e(metadata);
    double value = 123.5;
    std::string s = argc > 2 ? unhex(argv[2]) : "";
    bool ok = e.parseValue(value, argc > 2 ? s.c_str() : nullptr);
    std::cout << ok << " " << bits(value);
  } else if (mode == "range") {
    ParamRangeElement e(metadata);
    Attrs a;
    for (int i = 2; i < argc; i += 2)
      a.values[argv[i]] = unhex(argv[i + 1]);
    e.load(a);
    range(e);
    std::cout << " | ";
    trace(a);
    a.trace.clear();
    e.save(a);
    std::cout << " | ";
    trace(a);
    std::cout << " | ";
    for (auto key :
         {"min", "max", "mid", "def", "steps", "units", "curve", "id"})
      std::cout << key << "=" << hex(a.values[key].c_str()) << ",";
  } else if (mode == "string") {
    StringElement e(metadata);
    Attrs a;
    if (argc > 2)
      a.values["text"] = unhex(argv[2]);
    a.values["id"] = "item";
    e.load(a);
    std::cout << hex(e.text()) << " | ";
    trace(a);
    a.trace.clear();
    e.save(a);
    std::cout << " | ";
    trace(a);
    std::cout << " | " << hex(a.values["text"].c_str()) << " "
              << hex(a.values["id"].c_str());
  } else if (mode == "list") {
    StringListElement list(metadata);
    for (int i = 2; i < argc; ++i) {
      auto *e = new StringElement(metadata);
      Attrs a;
      a.values["text"] = unhex(argv[i]);
      e->load(a);
      list.addChild(e);
    }
    std::cout << list.countStrings();
    for (int i = 0; i < list.countStrings(); ++i)
      std::cout << " " << hex(list.getString(i));
  } else if (mode == "lifetime") {
    auto *list = new StringListElement(metadata);
    for (int i = 0; i < 3; ++i)
      list->addChild(new LifetimeChild(metadata));
    assert(list->countStrings() == 3);
    delete list;
    assert(destroyedChildren == 3);
    std::cout << destroyedChildren;
  } else if (mode == "ctor") {
    std::string cls = argv[2];
    if (cls == "ParamRangeElement") {
      ParamRangeElement e(metadata);
      range(e);
    } else if (cls == "StringElement") {
      StringElement e(metadata);
      std::cout << hex(e.text());
    } else {
      StringListElement e(metadata);
      std::cout << e.countStrings();
    }
  } else if (mode == "dtor") {
    std::string cls = argv[2];
    bool deleting = std::string(argv[3]) == "D0";
    Element *e = cls == "ParamRangeElement"
                     ? static_cast<Element *>(new ParamRangeElement(metadata))
                 : cls == "StringElement"
                     ? static_cast<Element *>(new StringElement(metadata))
                     : static_cast<Element *>(new StringListElement(metadata));
    int childCount = argc > 4 ? std::atoi(argv[4]) : 0;
    for (int i = 0; i < childCount; ++i)
      e->addChild(new StringElement(metadata));
    tracked = e;
    if (deleting)
      delete e;
    else {
      if (cls == "ParamRangeElement")
        static_cast<ParamRangeElement *>(e)->~ParamRangeElement();
      else if (cls == "StringElement")
        static_cast<StringElement *>(e)->~StringElement();
      else
        static_cast<StringListElement *>(e)->~StringListElement();
    }
    std::cout << baseCalls << " " << deletes;
    tracked = nullptr;
    if (!deleting)
      ::operator delete(e);
  }
  std::cout << "\n";
}
