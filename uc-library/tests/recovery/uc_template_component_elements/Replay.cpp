#include "core/public/coreenumdef.h"
#include "presonus/uc/ComponentElement.hpp"
#include "presonus/uc/meta_element.hpp"
#include <cstdlib>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

namespace {
void *watchedParent = nullptr;
void *watchedChild = nullptr;
bool parentDeleted = false;
int childrenDeleted = 0;
void recordDelete(void *p) {
  if (p == watchedParent)
    parentDeleted = true;
  if (p == watchedChild)
    ++childrenDeleted;
}
std::string encode(const std::string &s) {
  if (s.empty())
    return "-";
  constexpr char hex[] = "0123456789abcdef";
  std::string result;
  for (unsigned char c : s) {
    result += hex[c >> 4];
    result += hex[c & 15];
  }
  return result;
}
std::string decode(const std::string &s) {
  if (s == "-")
    return {};
  std::string result;
  for (std::size_t i = 0; i < s.size(); i += 2)
    result += static_cast<char>(std::stoi(s.substr(i, 2), nullptr, 16));
  return result;
}
class TraceAttributes final : public Presonus::UC::ElementAttributes {
public:
  Core::Portable::Attributes storage{
      Core::Portable::AttributeAllocator::getDefault()};
  Presonus::UC::LocalElementAttributes actual{storage};
  mutable std::vector<std::string> gets;
  std::vector<std::pair<std::string, std::string>> stores;
  Core::CStringPtr lookupName(Core::CStringPtr key) const override {
    gets.emplace_back(key);
    return actual.lookupName(key);
  }
  void storeName(Core::CStringPtr key, Core::CStringPtr value) override {
    stores.emplace_back(key, value ? value : "");
    actual.storeName(key, value);
  }
};
template <class T> void run(int phase, int children, int count) {
  Presonus::UC::MetaElement metadata("portable-test", nullptr);
  TraceAttributes attributes;
  for (int i = 0; i < count; ++i) {
    std::string key, value;
    std::cin >> key >> value;
    const auto k = decode(key), v = decode(value);
    attributes.actual.storeName(k.c_str(), v.c_str());
  }
  auto *element = new T(metadata);
  if (phase == 2 || phase == 3) {
    watchedParent = element;
    parentDeleted = false;
    childrenDeleted = 0;
    if (children) {
      auto *child = new T(metadata);
      watchedChild = child;
      element->addChild(child);
    }
    bool observedParentDelete;
    if (phase == 2) {
      element->~T();
      observedParentDelete = parentDeleted;
      ::operator delete(element);
    } else {
      delete element;
      observedParentDelete = parentDeleted;
    }
    std::cout << observedParentDelete << ' ' << childrenDeleted << '\n';
    watchedParent = nullptr;
    watchedChild = nullptr;
    return;
  }
  if (phase == 5) {
    TraceAttributes initial;
    for (const auto *key :
         {"id", "inherit", "paramlist", "classname", "classfallback",
          "classdata", "template", "name", "group"})
      initial.actual.storeName(key, "seed");
    initial.actual.storeName("flags", "public mutable private-params");
    element->load(initial);
    attributes.gets = initial.gets;
  }
  if (phase == 1 || phase == 5)
    element->load(attributes);
  element->save(attributes);
  std::cout << attributes.gets.size();
  for (const auto &key : attributes.gets)
    std::cout << ' ' << encode(key);
  std::cout << ' ' << attributes.stores.size();
  for (const auto &pair : attributes.stores)
    std::cout << ' ' << encode(pair.first) << ' ' << encode(pair.second);
  std::cout << '\n';
  delete element;
}
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  recordDelete(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  recordDelete(p);
  __real__ZdlPvm(p, size);
}
int main() {
  int cls, phase, children, count;
  while (std::cin >> cls >> phase >> children >> count) {
    if (phase == 4) {
      std::string flagsText, fieldText;
      std::cin >> flagsText >> fieldText;
      const auto flagsInput = decode(flagsText), fieldInput = decode(fieldText);
      const Core::EnumInfo table[] = {
          {"public", 1}, {"mutable", 2}, {"private-params", 4}, {nullptr, 0}};
      int flags = Core::EnumInfo::parseMultiple(
          Core::ConstString(flagsInput.c_str()), table);
      Core::CString64 field(fieldInput.c_str());
      Core::CString128 printed;
      Core::EnumInfo::printMultiple(printed, flags, table);
      std::cout << flags << ' ' << encode(field.str()) << ' '
                << encode(printed.str()) << '\n';
    } else if (cls)
      run<Presonus::UC::ComponentElement>(phase, children, count);
    else
      run<Presonus::UC::TemplateElement>(phase, children, count);
  }
}
