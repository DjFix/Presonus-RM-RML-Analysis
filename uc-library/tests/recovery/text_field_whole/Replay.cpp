#include "presonus/panel/FieldElement.hpp"
#include "presonus/panel/LCDManager.hpp"
#include "presonus/panel/TextEntryElement.hpp"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using namespace Presonus::Panel;
namespace {
void *watched = nullptr;
bool deleted = false;
std::string rect(const Rectangle &r) {
  return std::to_string(r.x) + " " + std::to_string(r.y) + " " +
         std::to_string(r.width) + " " + std::to_string(r.height);
}
class Display final : public IDisplay {
public:
  std::vector<std::string> events;
  int x = 0, y = 0;
  void setPort(IPanelIO *) override {}
  int getScreenWidth() const override { return 320; }
  int getScreenHeight() const override { return 240; }
  int getCharHeight() const override { return 8; }
  int getTextBoxHeight() const override {
    const_cast<Display *>(this)->events.push_back("height");
    return 9;
  }
  void copyBits(char *, const char *, const Point &,
                const Rectangle &) override {}
  void copyBits(const char *, const Point &, const Rectangle &) override {}
  void getScreenBits(char *, const Point &, const Rectangle &) override {}
  void clear() override {}
  void fillRect(const Rectangle &r) override {
    events.push_back("fill " + rect(r));
  }
  void eraseRect(const Rectangle &r) override {
    events.push_back("erase " + rect(r));
  }
  void invertRect(const Rectangle &r) override {
    events.push_back("invert " + rect(r));
  }
  void setPixel(int, int, bool) override {}
  bool getPixel(int, int) const override { return false; }
  void drawText(int, int, const char *, int, Rectangle *) override {}
  void drawString(const char *text, int flags, Rectangle *r) override {
    events.push_back("text " + std::string(text) + " " + std::to_string(flags) +
                     " " + (r ? "1" : "0"));
    if (r)
      *r = {x, y, static_cast<int>(std::strlen(text)) * 6, *text ? 8 : 0};
  }
  char *getBitmapData() const override { return nullptr; }
  int pixelLength(const char *text) override {
    events.push_back("pixel " + std::string(text));
    return std::strlen(text) * 6;
  }
  int setPen(int) override { return 0; }
  int setTextColor(int color) override {
    events.push_back("color " + std::to_string(color));
    return 0;
  }
  void moveTo(int xx, int yy) override {
    x = xx;
    y = yy;
    events.push_back("move " + std::to_string(x) + " " + std::to_string(y));
  }
  void getPos(int &xx, int &yy) const override {
    xx = x;
    yy = y;
  }
  void update(bool) override {}
};
class Delegate final : public ILCDDelegate {
public:
  Core::Portable::Parameter *parameter = nullptr;
  mutable unsigned lookups = 0;
  Core::Portable::Parameter *
  lookupElementParameter(const char *name) const override {
    assert(std::strcmp(name, "level") == 0);
    ++lookups;
    return parameter;
  }
};
ElementInfo info(int color = 0) {
  ElementInfo i;
  auto word = [&](unsigned offset, int value) {
    for (unsigned j = 0; j < 4; ++j)
      i.observation[offset + j] =
          (static_cast<unsigned>(value) >> (j * 8)) & 255;
  };
  word(4, 10);
  word(8, 20);
  word(12, 7);
  word(84, color);
  std::memcpy(i.observation.data() + 20, "level", 6);
  return i;
}
void lifecycle() {
  Core::Portable::ParamInfo pi{};
  std::strcpy(pi.name, "level");
  Delegate delegate;
  FieldElement::defaultLookupManager().setDelegate(&delegate);
  auto *parameter = new Core::Portable::StringParam(pi);
  parameter->fromString("hello", false);
  delegate.parameter = parameter;
  auto *text = new TextEntryElement(info());
  Core::CString128 output;
  text->getDrawString(output, 32);
  assert(std::strcmp(output.str(), "hello") == 0 && delegate.lookups);
  // Existing shared/copy semantics survive either owner's destruction.
  auto copy = *text;
  TextEntryElement::setEncoderParam(parameter);
  watched = text;
  deleted = false;
  delete text;
  assert(deleted);
  watched = nullptr;
  TextEntryElement::setEncoderParam(nullptr);
  parameter->fromString("changed", false);
  copy.getDrawString(output, 32);
  assert(std::strcmp(output.str(), "changed") == 0);
  delegate.parameter = nullptr;
  delete parameter;
  assert(copy.fieldElement()->cachedParameter() == nullptr);
  copy.getDrawString(output, 32);
  assert(output.isEmpty());
  FieldElement::defaultLookupManager().setDelegate(nullptr);
  Element base(info());
  assert(base.elementState().x == 10 && base.elementState().y == 20);
  assert(base.sourceInfo().observation == info().observation &&
         base.drawingBounds().width == 0);
  OffscreenElement off(info());
  assert(off.elementState().dirty == 1);
  std::cout << "lifecycle-provider-copy-delete-ok\n";
}
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched)
    deleted = true;
  __real__ZdlPv(p);
}
int main(int argc, char **argv) {
  if (argc == 1) {
    lifecycle();
    return 0;
  }
  assert(argc == 11);
  const std::string mode = argv[1], input = argv[2];
  const int cursor = std::atoi(argv[3]), delta = std::atoi(argv[4]),
            color = std::atoi(argv[5]), force = std::atoi(argv[6]);
  const bool param = std::atoi(argv[7]), enabled = std::atoi(argv[8]);
  const int message = std::atoi(argv[9]);
  const std::string repeat = argv[10];
  Core::Portable::ParamInfo pi{};
  std::strcpy(pi.name, "level");
  Core::Portable::StringParam parameter(pi);
  parameter.fromString(input.c_str(), false);
  parameter.enable(enabled);
  parameter.setDefaultText("fallback");
  Delegate delegate;
  delegate.parameter = param ? &parameter : nullptr;
  FieldElement::defaultLookupManager().setDelegate(&delegate);
  FieldElement field(info(color));
  presonus::panel::portable::TextEntryState state;
  state.cursor = cursor;
  state.dirty = true;
  std::strncpy(state.text.data(), input.c_str(), 31);
  TextEntryElement text(state, field);
  Display display;
  Core::CString128 buffer;
  if (repeat != "none") {
    if (mode == "fieldrender")
      field.render(display, force);
    else if (mode == "textdraw") {
      field.activate(force);
      text.draw(display);
    } else
      text.render(display, force);
    const std::string updated = repeat == "same"    ? input
                                : repeat == "short" ? "a"
                                                    : "";
    parameter.fromString(updated.c_str(), false);
    std::strncpy(state.text.data(), updated.c_str(), 31);
    display.events.clear();
  }
  int result = -1;
  if (mode == "delta" || mode == "set" || mode == "current" || mode == "char" ||
      mode == "tap" || mode == "next") {
    field.setDirty(0);
    state.dirty = false;
  }
  if (mode == "delta")
    result = text.deltaEncoder(delta);
  else if (mode == "set")
    text.setCurrentChar('X');
  else if (mode == "current")
    result = static_cast<unsigned char>(text.getCurrentChar());
  else if (mode == "char")
    result = static_cast<unsigned char>(text.getChar(cursor));
  else if (mode == "tap")
    result = text.tap();
  else if (mode == "next")
    result = text.next();
  else if (mode == "textformat")
    text.getDrawString(buffer, 32);
  else if (mode == "fieldformat")
    field.getDrawString(buffer, 32);
  else if (mode == "helper")
    field.getDrawString(param ? &parameter : nullptr, buffer, 32);
  else if (mode == "textdraw") {
    field.activate(force);
    text.draw(display);
  } else if (mode == "textrender")
    text.render(display, force);
  else if (mode == "fieldrender")
    field.render(display, force);
  else if (mode == "changed") {
    field.getParam();
    field.setDirty(0);
    text.paramChanged(&parameter, message);
  } else
    std::abort();
  std::cout << "{\"text\":"
            << std::quoted(param ? parameter.getText().str()
                                 : state.text.data())
            << ",\"cursor\":" << state.cursor
            << ",\"remainder\":" << state.encoderRemainder
            << ",\"dirty\":" << field.elementState().dirty << ",\"events\":[";
  bool first = true;
  for (const auto &event : display.events) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << std::quoted(event);
  }
  std::cout << "],\"return\":" << result
            << ",\"formatted\":" << std::quoted(buffer.str())
            << ",\"current\":[" << field.drawingBounds().x << ','
            << field.drawingBounds().y << ',' << field.drawingBounds().width
            << ',' << field.drawingBounds().height << "],\"previous\":["
            << field.previousBounds().x << ',' << field.previousBounds().y
            << ',' << field.previousBounds().width << ','
            << field.previousBounds().height << "]}\n";
  FieldElement::defaultLookupManager().setDelegate(nullptr);
}
