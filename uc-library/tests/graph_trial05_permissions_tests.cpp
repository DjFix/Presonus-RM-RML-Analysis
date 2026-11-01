#include "core/portable/corefilename.h"
#include "presonus/mixer/PermissionsComponent.hpp"
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using Presonus::Mixer::PermissionsBindings;
using Presonus::Mixer::PermissionsComponent;
namespace {
std::string quote(const std::string &s) {
  std::ostringstream out;
  out << '"';
  for (unsigned char c : s) {
    if (c == '"' || c == '\\')
      out << '\\';
    out << c;
  }
  out << '"';
  return out.str();
}
struct Capture {
  PermissionsComponent *self = nullptr;
  PermissionsBindings *bindings = nullptr;
  Core::Portable::FileName *output = nullptr;
  std::vector<std::string> trace;
};
struct OwnerCapture {
  Capture *capture;
};
class ObservedStringParam : public Core::Portable::StringParam {
public:
  ObservedStringParam(const Core::Portable::ParamInfo &info, Capture &capture,
                      const char *name)
      : StringParam(info), capture_(capture), name_(name) {}
  void toString(char *output, int size) const override {
    capture_.trace.push_back("[\"toString\"," + quote(name_) + "," +
                             std::to_string(size) + "]");
    StringParam::toString(output, size);
  }
  void fromString(Core::CStringPtr string, bool edit) override {
    capture_.trace.push_back("[\"fromString\"," + quote(name_) + "," +
                             quote(string) + "," + (edit ? "1" : "0") + "]");
    StringParam::fromString(string, edit);
  }

private:
  Capture &capture_;
  std::string name_;
};
void getFileName(void *ctx, const PermissionsComponent &self,
                 Core::Portable::FileName &output,
                 const Core::CStringBuffer<64> &name) {
  auto &c = *static_cast<Capture *>(ctx);
  c.trace.push_back(std::string("[\"getFileName\",") +
                    (&self == c.self ? "true" : "false") + "," +
                    (&output == c.output ? "true" : "false") + "," +
                    (&name == c.bindings->selectedName ? "true" : "false") +
                    "," + quote(name.str()) + "]");
}
void load(void *ctx, PermissionsComponent &self) {
  auto &c = *static_cast<Capture *>(ctx);
  c.trace.push_back(std::string("[\"loadSelectedDevice\",") +
                    (&self == c.self ? "true" : "false") + "," +
                    std::to_string(c.bindings->dirty) + "]");
}
void changed(void *ctx, PermissionsComponent &self) {
  auto &c = *static_cast<OwnerCapture *>(ctx)->capture;
  c.trace.push_back(std::string("[\"devicePermissionsChanged\",") +
                    (ctx == c.bindings->ownerContext ? "true" : "false") + "," +
                    (&self == c.self ? "true" : "false") + "," +
                    std::to_string(c.bindings->dirty) + "]");
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 8)
    return 2;
  const int target = std::atoi(argv[1]);
  Capture capture;
  OwnerCapture owner{&capture};
  Core::Portable::ParamInfo info = PARAM_STRING(1, "permission", 0);
  ObservedStringParam mix(info, capture, "mix"), other(info, capture, "other");
  mix.Core::Portable::StringParam::fromString(argv[4], false);
  other.Core::Portable::StringParam::fromString(argv[4], false);
  Core::CStringBuffer<64> name(argv[3]);
  PermissionsBindings bindings;
  bindings.mix = &mix;
  bindings.other = &other;
  bindings.selectedName = std::atoi(argv[2]) ? &name : nullptr;
  bindings.restricted = static_cast<unsigned char>(std::atoi(argv[6]));
  bindings.dirty = static_cast<unsigned char>(std::atoi(argv[7]));
  bindings.context = &capture;
  bindings.ownerContext = &owner;
  bindings.getFileName = getFileName;
  bindings.loadSelectedDevice = load;
  bindings.devicePermissionsChanged = changed;
  PermissionsComponent component(bindings);
  capture.self = &component;
  capture.bindings = &bindings;
  Core::CStringBuffer<128> output;
  std::memset(output.getBuffer(), 0x7e, 128);
  std::memcpy(output.getBuffer(), "keep", 5);
  Core::Portable::FileName fileName;
  std::memset(fileName.getBuffer(), 0, 256);
  std::memcpy(fileName.getBuffer(), output.getBuffer(), 128);
  capture.output = &fileName;
  switch (target) {
  case 0:
    component.getSelectedFileName(fileName);
    break;
  case 1:
    component.getMixString(output);
    break;
  case 2:
    component.getOtherString(output);
    break;
  case 3:
    component.auxLinkingChanged();
    break;
  case 4:
    component.setFullPermissions(std::atoi(argv[5]) != 0);
    break;
  default:
    return 3;
  }
  std::cout << "{\"trace\":[";
  for (std::size_t i = 0; i < capture.trace.size(); ++i)
    std::cout << (i ? "," : "") << capture.trace[i];
  std::cout << "],\"output_hex\":\"";
  for (int i = 0; i < 128; ++i)
    std::cout << std::hex << std::setw(2) << std::setfill('0')
              << static_cast<unsigned>(static_cast<unsigned char>(
                     (target == 0 ? fileName.getBuffer()
                                  : output.getBuffer())[i]));
  std::cout << "\",\"dirty\":" << std::dec << static_cast<int>(bindings.dirty)
            << "}\n";
}
