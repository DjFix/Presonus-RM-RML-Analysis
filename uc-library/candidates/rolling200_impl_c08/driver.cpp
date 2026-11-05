#include "presonus/dsp/ControllerInfo.hpp"
#include <bit>
#include <cassert>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using namespace Presonus::Dsp;
class TestController : public Controller {
public:
  TestController() : Controller(presonus::dsp::ControllerSourceTag{}) {}
  float getValue(int) const override { return 9.f; }
  float setValue(int, float v) override { return v; }
  void doUpdates() override {}
};
class Boundary : public Core::Formatter {
public:
  bool success = false;
  mutable std::string trace;
  void capture(Data &d) const {
    std::ostringstream s;
    s << "[\"formatter\"," << (d.object ? 1 : 0) << ","
      << static_cast<std::uint32_t>(d.size) << ","
      << std::bit_cast<unsigned>(d.value) << ","
      << std::bit_cast<unsigned>(d.range->minValue) << ","
      << std::bit_cast<unsigned>(d.range->maxValue) << "]";
    trace = s.str();
  }
  void print(Data &d) const override {
    capture(d);
    if (d.size > 0) {
      std::snprintf(d.string, d.size, "%s", "provider");
      // Output fixture observes the full declared writable range.
      const auto used = std::char_traits<char>::length(d.string) + 1;
      for (int i = static_cast<int>(used); i < d.size; ++i)
        d.string[i] = 0;
    }
  }
  bool scan(Data &d) const override {
    capture(d);
    d.value = 42.5f;
    return success;
  }
};
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream in(argv[1]);
  assert(in);
  std::string kind, input;
  int mode, fmt, cap, integer, range, success, match, index;
  unsigned value, flags, size;
  while (in >> kind >> mode >> fmt >> value >> cap >> integer >> range >>
         std::quoted(input) >> success >> flags >> size >> match >> index) {
    TestController c;
    ParamDescriptor d(presonus::dsp::DescriptorSourceTag{}),
        first(presonus::dsp::DescriptorSourceTag{});
    Boundary boundary;
    boundary.success = success;
    Core::LinearInterpolator curve(-10.f, 20.f);
    for (auto *p : {&d, &first}) {
      auto &s = p->sourceState();
      s.tag = p == &d ? 77 : 12;
      s.flags = 0x100a0;
      s.word10 = integer;
      s.word14 = std::bit_cast<unsigned>(0.375f);
      s.text0 = "alpha";
      s.text1 = "beta";
      s.text2 = "gamma";
      s.formatter = fmt ? &boundary : nullptr;
      s.interpolator = range ? &curve : nullptr;
    }
    Core::Vector<ParamDescriptor *> list;
    list.add(&first);
    list.add(mode == 3 ? nullptr : &d);
    c.sourceState().descriptors = mode == 2 ? nullptr : &list;
    c.sourceState().lookupByTag = mode == 1;
    c.sourceState().word08 = match ? 77 : 0xffffffffu;
    int tag = mode == 1 ? 77 : mode == 4 ? 99 : 1;
    char buffer[256];
    std::fill(std::begin(buffer), std::end(buffer), 'Z');
    std::cout << "{";
    if (kind == "print") {
      Presonus::StringResult result{buffer, cap};
      c.printValue(result, tag, std::bit_cast<float>(value));
      std::cout << "\"output_hex\":\"";
      const char *hex = "0123456789abcdef";
      for (int i = 0; i < cap; ++i) {
        auto byte = static_cast<unsigned char>(buffer[i]);
        std::cout << hex[byte >> 4] << hex[byte & 15];
      }
      std::cout << "\"";
    } else if (kind == "scan") {
      float output = std::bit_cast<float>(0xdeadbeefu);
      auto ok = c.scanValue(output, tag, input.c_str());
      std::cout << "\"return\":" << ok
                << ",\"output\":" << std::bit_cast<unsigned>(output);
    } else if (kind == "info") {
      ParamInfo info;
      info.flags = flags;
      info.byteSize = size;
      info.text2 = "<unchanged>";
      c.getParameterInfo(info, tag);
      std::cout << "\"output\":[" << static_cast<unsigned>(info.tag) << ",\""
                << info.text0 << "\",\"" << info.text1 << "\"," << info.flags
                << "," << info.word10 << "," << info.word14 << ","
                << info.byteSize << ",\"" << info.text2 << "\"]";
    } else {
      auto output = c.Controller::getValue(index);
      std::cout << "\"return\":" << std::bit_cast<unsigned>(output);
    }
    std::cout << ",\"formatter\":"
              << (boundary.trace.empty() ? "null" : boundary.trace) << "}\n";
    for (auto *p : {&d, &first}) {
      p->sourceState().flags = 0;
      p->sourceState().interpolator = nullptr;
    }
  }
  // Source provider observations, separate from original ARM execution:
  // actual pinned Core formatter behavior, rather than fake Core classes.
  const auto &provider = Core::IntFormatter::instance();
  Core::Formatter::Range r{-10.f, 20.f};
  char out[32]{};
  Core::Formatter::Data data{nullptr, out, 32, 12.f, &r};
  provider.print(data);
  assert(std::string(out) == "12");
  data.string = const_cast<char *>("-7");
  data.size = -1;
  data.value = 0.f;
  assert(provider.scan(data) && data.value == -7.f);
  std::cerr
      << "actual pinned Core::IntFormatter print/scan observations passed\n";
}
