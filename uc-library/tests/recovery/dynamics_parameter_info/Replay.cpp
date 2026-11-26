#include "core/portable/coreparams.h"
#include "presonus/mixer/DynamicsParameterInfo.hpp"
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>

static std::string hex(const char *p, std::size_t n) {
  if (!p)
    return "null";
  constexpr char digits[] = "0123456789abcdef";
  std::string result;
  for (std::size_t i = 0; i < n; ++i) {
    auto v = static_cast<unsigned char>(p[i]);
    result += digits[v >> 4];
    result += digits[v & 15];
  }
  return result;
}
static std::string text(const char *p) {
  return p ? hex(p, std::strlen(p) + 1) : "null";
}
static std::uint32_t bits(float f) {
  std::uint32_t b;
  std::memcpy(&b, &f, sizeof(b));
  return b;
}
int main() {
  using namespace Core::Portable;
  using namespace presonus::mixer_parameter_info;
  for (auto array : {Gate, Compressor}) {
    ParamList list;
    list.add(array, 10);
    if (list.count() != 10)
      return 1;
    for (int i = 0; i < 10; ++i) {
      const auto &p = array[i];
      auto *v = list.at(i);
      if (!v || list.byTag(p.tag) != v || list.find(p.name) != v ||
          v->getType() != p.type || v->getTag() != p.tag ||
          std::strcmp(v->getName(), p.name) || v->isOwnInfo() ||
          bits(v->getMin()) != bits(p.minValue) ||
          bits(v->getMax()) != bits(p.maxValue) ||
          bits(v->getDefault()) != bits(p.defaultValue) ||
          bits(v->getValue()) != bits(p.defaultValue) ||
          text(v->getTitle()) != text(p.title) ||
          text(v->getTitle(true)) !=
              text(p.shortTitle && *p.shortTitle ? p.shortTitle : p.title) ||
          v->isStorable() != bool(p.flags & ParamInfo::kStorable) ||
          v->isPublic() != !bool(p.flags & ParamInfo::kPrivate) ||
          v->isLinkable() != bool(p.flags & ParamInfo::kLinkable) ||
          v->isMutable() != bool(p.flags & ParamInfo::kMutable) ||
          v->isReadOnly() != bool(p.flags & ParamInfo::kReadOnly) ||
          v->isUserFlag1() != bool(p.flags & ParamInfo::kUserFlag1) ||
          v->isUserFlag2() != bool(p.flags & ParamInfo::kUserFlag2))
        return 2;
      std::cout << std::dec << p.type << ' ' << p.tag << ' ' << hex(p.name, 32);
      for (auto f :
           {p.minValue, p.maxValue, p.midValue, p.defaultValue, p.deltaValue})
        std::cout << ' ' << std::hex << std::setfill('0') << std::setw(8)
                  << bits(f);
      std::cout << ' ' << std::dec << p.flags;
      for (auto s : {p.unitName, p.curveName})
        std::cout << ' ' << text(s);
      std::cout << ' ' << (p.stringList ? "nonnull" : "null") << ' '
                << text(p.title) << ' ' << text(p.shortTitle);
      auto *numeric = static_cast<NumericParam *>(v);
      std::cout << ' ' << (v->getFormatter() ? 1 : 0) << ' '
                << (numeric->getInterpolator() ? 1 : 0) << '\n';
    }
  }
}
