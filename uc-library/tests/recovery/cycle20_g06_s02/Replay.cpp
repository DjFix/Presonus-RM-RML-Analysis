#include "presonus/panel/Element.hpp"
#include "presonus/surface_panel/IDisplay.hpp"

#include <array>
#include <cstdio>
#include <cstring>

using namespace Presonus::Panel;

namespace {
class DisplayCapture final : public IDisplay {
public:
  mutable int calls = 0;
  void setPort(IPanelIO *) override { ++calls; }
  int getScreenWidth() const override {
    ++calls;
    return {};
  }
  int getScreenHeight() const override {
    ++calls;
    return {};
  }
  int getCharHeight() const override {
    ++calls;
    return {};
  }
  int getTextBoxHeight() const override {
    ++calls;
    return {};
  }
  void copyBits(char *, const char *, const Point &,
                const Rectangle &) override {
    ++calls;
  }
  void copyBits(const char *, const Point &, const Rectangle &) override {
    ++calls;
  }
  void getScreenBits(char *, const Point &, const Rectangle &) override {
    ++calls;
  }
  void clear() override { ++calls; }
  void fillRect(const Rectangle &) override { ++calls; }
  void eraseRect(const Rectangle &) override { ++calls; }
  void invertRect(const Rectangle &) override { ++calls; }
  void setPixel(int, int, bool) override { ++calls; }
  bool getPixel(int, int) const override {
    ++calls;
    return {};
  }
  void drawText(int, int, const char *, int, Rectangle *) override { ++calls; }
  void drawString(const char *, int, Rectangle *) override { ++calls; }
  char *getBitmapData() const override {
    ++calls;
    return {};
  }
  int pixelLength(const char *) override {
    ++calls;
    return {};
  }
  int setPen(int) override {
    ++calls;
    return {};
  }
  int setTextColor(int) override {
    ++calls;
    return {};
  }
  void moveTo(int, int) override { ++calls; }
  void getPos(int &, int &) const override { ++calls; }
  void update(bool) override { ++calls; }
};

struct DerivedElement final : Element {
  int marker = 0x5648;
};

void render(Element &element, DisplayCapture &display, bool force) {
  std::array<unsigned char, sizeof(Element)> before;
  std::memcpy(before.data(), &element, before.size());
  element.Element::render(display, force);
  std::printf("%d %d %d\n", static_cast<int>(force), display.calls,
              std::memcmp(before.data(), &element, before.size()) == 0);
}
} // namespace

int main() {
  Element element;
  DerivedElement derived;
  DisplayCapture first;
  DisplayCapture second;
  render(element, first, false);
  render(element, first, true);
  render(derived, second, false);
  render(derived, second, true);
  return derived.marker == 0x5648 ? 0 : 1;
}
