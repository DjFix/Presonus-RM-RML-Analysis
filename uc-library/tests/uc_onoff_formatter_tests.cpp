#include "presonus/uc/OnOff.hpp"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
using OnOff = Presonus::UC::Format::OnOff;
extern "C" void
ctor1(OnOff *, const char *, const char *,
      const char *) asm("_ZN8Presonus2UC6Format5OnOffC1EPKcS4_S4_");
extern "C" void
ctor2(OnOff *, const char *, const char *,
      const char *) asm("_ZN8Presonus2UC6Format5OnOffC2EPKcS4_S4_");
extern "C" void dtor1(OnOff *) asm("_ZN8Presonus2UC6Format5OnOffD1Ev");
extern "C" void dtor0(OnOff *) asm("_ZN8Presonus2UC6Format5OnOffD0Ev");
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
static void *watched;
static unsigned sized, unsized;
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched) {
    ++unsized;
    watched = nullptr;
  }
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == watched) {
    ++sized;
    watched = nullptr;
  }
  __real__ZdlPvm(p, n);
}
static std::string decode(const std::string &s) {
  if (s == "-" || s == "_")
    return {};
  std::string result;
  for (std::size_t i = 0; i < s.size(); i += 2)
    result.push_back(
        static_cast<char>(std::stoul(s.substr(i, 2), nullptr, 16)));
  return result;
}
static float fromWord(std::uint32_t word) {
  float value;
  std::memcpy(&value, &word, sizeof value);
  return value;
}
static std::uint32_t wordOf(float value) {
  std::uint32_t word;
  std::memcpy(&word, &value, sizeof word);
  return word;
}
__attribute__((noinline)) static void dispatch(Core::Formatter *f,
                                               Core::Formatter::Data &d,
                                               bool scan, bool expected) {
  if (scan)
    assert(f->scan(d) == expected);
  else
    f->print(d);
}
__attribute__((noinline)) static void baseDelete(Core::Formatter *p) {
  delete p;
}
__attribute__((noinline)) static void typedDelete(OnOff *p) { delete p; }
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream input(argv[1]);
  assert(input);
  std::string line;
  unsigned rows = 0, lifetimes = 0;
  while (std::getline(input, line)) {
    std::istringstream s(line);
    std::string kind, on, off, text, output;
    std::uint32_t before, after;
    unsigned ok;
    s >> kind >> on >> off >> text >> before >> ok >> after >> output;
    assert(s && (kind == "P" || kind == "S"));
    auto a = decode(on), b = decode(off), t = decode(text),
         expected = decode(output);
    OnOff f("onoff", on == "-" ? nullptr : a.c_str(),
            off == "-" ? nullptr : b.c_str());
    char buffer[256]{};
    std::strcpy(buffer, t.c_str());
    Core::Formatter::Data d{nullptr, text == "-" ? nullptr : buffer, 1,
                            fromWord(before), nullptr};
    dispatch(&f, d, kind == "S", ok != 0);
    assert(wordOf(d.value) == after);
    if (kind == "P")
      assert(std::string(buffer) == expected);
    ++rows;
  }
  for (auto ctor : {ctor1, ctor2}) {
    for (unsigned cleanup = 0; cleanup != 4; ++cleanup) {
      char on[] = "YES", off[] = "NO";
      auto *p = static_cast<OnOff *>(::operator new(sizeof(OnOff)));
      watched = p;
      const auto frees = sized + unsized;
      ctor(p, "onoff", on, off);
      assert(std::strcmp(p->getName(), "onoff") == 0);
      char buffer[16];
      Core::Formatter::Data d{nullptr, buffer, 1, 1.f, nullptr};
      dispatch(p, d, false, false);
      assert(std::strcmp(buffer, "YES") == 0);
      on[0] = 'Z';
      dispatch(p, d, false, false);
      assert(std::strcmp(buffer, "ZES") == 0); // actual borrowed label effect
      auto **vtable = *reinterpret_cast<void ***>(p);
      assert(vtable[0] == reinterpret_cast<void *>(dtor1));
      assert(vtable[1] == reinterpret_cast<void *>(dtor0));
      if (cleanup == 0) {
        dtor1(p);
        assert(watched == p && sized + unsized == frees);
        ::operator delete(p);
      } else if (cleanup == 1)
        dtor0(p);
      else if (cleanup == 2)
        baseDelete(p);
      else
        typedDelete(p);
      assert(watched == nullptr && sized + unsized == frees + 1);
      ++lifetimes;
    }
  }
  assert(rows > 300 && lifetimes == 8);
  std::printf("{\"passed\":true,\"rows\":%u,\"lifetimes\":%u,\"sized\":%u,"
              "\"unsized\":%u,\"real_forwarded_deletes\":true}\n",
              rows, lifetimes, sized, unsized);
}
