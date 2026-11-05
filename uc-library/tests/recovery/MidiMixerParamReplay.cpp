#include "presonus/surface/MidiMixerHandler.hpp"
#include <cstring>
#include <iostream>
#include <sstream>
using namespace Core::Portable;
namespace {
std::vector<std::string> trace;
std::string hex(const char *s) {
  const char *digits = "0123456789abcdef";
  std::string out;
  for (const unsigned char *p = reinterpret_cast<const unsigned char *>(s); *p;
       ++p) {
    out += digits[*p >> 4];
    out += digits[*p & 15];
  }
  return out;
}
std::string unhex(const std::string &s) {
  std::string out;
  for (size_t i = 0; i < s.size(); i += 2)
    out += static_cast<char>(std::stoul(s.substr(i, 2), nullptr, 16));
  return out;
}
struct Local : Component {
  void add(Parameter *p) { paramList.add(p); }
  void detach(Parameter *p) { paramList.remove(p); }
};
struct Number : NumericParam {
  Local &local;
  mutable std::function<void()> mutation;
  Number(const ParamInfo &info, Local &local)
      : NumericParam(info), local(local) {}
  void setRaw(unsigned bits) { std::memcpy(&value, &bits, 4); }
  float getValue() const override {
    float v = NumericParam::getValue();
    unsigned bits;
    std::memcpy(&bits, &v, 4);
    trace.push_back("value " + std::to_string(bits));
    if (mutation) {
      auto f = std::move(mutation);
      mutation = {};
      f();
    }
    return v;
  }
};
struct Output : StringParam {
  using StringParam::StringParam;
  void fromString(const char *s, bool edit) override {
    trace.push_back("output " + std::to_string(edit) + " " + hex(s));
    StringParam::fromString(s, edit);
    if (std::strcmp(getText().str(), s) != 0)
      std::abort();
  }
};
struct Services : presonus::surface::midi_port::Services {
  void setDefaultColor(const std::string &) override {}
  bool recordParameterPresent() override {
    trace.push_back("record-present");
    return true;
  }
  float recordParameterValue() override {
    trace.push_back("record-value");
    return 1;
  }
  void updateRecordMapping(bool b) override {
    trace.push_back("record-map " + std::to_string(b));
  }
  bool idleSlotPresent(unsigned) override { return false; }
  void invokeIdleSlot(unsigned) override {}
};
} // namespace
extern "C" Parameter *
__real__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *,
                                                         int);
extern "C" Parameter *
__wrap__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *c,
                                                         int tag) {
  auto *p = __real__ZNK4Core8Portable9Component17getParameterByTagEi(c, tag);
  trace.push_back("lookup " + std::to_string(tag) + " " +
                  std::to_string(p != nullptr));
  return p;
}
int main(int argc, char **argv) {
  if (argc > 1 && std::string(argv[1]) == "insert") {
    Core::CString256 s(unhex(argv[2]).c_str());
    s.insert(std::stoi(argv[3]), argv[4]);
    std::cout << hex(s.str()) << '\n';
    return 0;
  }
  if (argc != 8)
    return 2;
  int tag = std::stoi(argv[1]), cast = std::stoi(argv[2]),
      mode = std::stoi(argv[3]);
  unsigned first = std::stoul(argv[4]), second = std::stoul(argv[5]);
  auto text = unhex(argv[6]);
  int mutation = std::stoi(argv[7]);
  ParamInfo inInfo = PARAM_STRING(4, "input", 0);
  inInfo.tag = tag;
  ParamInfo modeInfo =
      PARAM_FLOAT(5, "mode", -100, 100, 0, 1, nullptr, nullptr, 0, 0);
  ParamInfo outInfo = PARAM_STRING(2, "output", 0);
  Local local;
  auto *a = new Number(modeInfo, local);
  auto *b = new Number(modeInfo, local);
  a->setRaw(first);
  b->setRaw(second);
  auto *out = new Output(outInfo);
  local.add(out);
  bool aAttached = mode != 0, bAttached = false;
  if (mode)
    local.add(a);
  a->mutation = [&] {
    if (mutation) {
      local.detach(a);
      aAttached = false;
      if (mutation == 1) {
        local.add(b);
        bAttached = true;
      }
    }
  };
  StringParam str(inInfo);
  str.fromString(text.c_str(), false);
  NumericParam numeric(inInfo);
  presonus::surface::midi_port::State state;
  state.localParameters = &local;
  Services services;
  Presonus::Surface::MidiMixerHandler handler(state, services);
  trace.clear();
  handler.paramChanged(cast ? static_cast<Parameter *>(&str) : &numeric, -17);
  for (const auto &event : trace)
    std::cout << event << '\n';
  // ParamList owns its current elements; remove detached/unused test objects.
  if (!aAttached)
    delete a;
  if (!bAttached)
    delete b;
}
