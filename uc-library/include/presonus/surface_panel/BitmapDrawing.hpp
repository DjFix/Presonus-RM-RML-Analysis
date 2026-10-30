#pragma once
#include "core/portable/coresingleton.h"
#include "core/system/corethread.h"
#include "presonus/surface_panel/IDisplay.hpp"
#include <array>
#include <cstdint>

namespace presonus::surface_panel_port {
struct BitmapDrawingAccess;
}
namespace Presonus::Panel {
class IPanelIO;
// Application source port with complete measured IDisplay and actual CCL
// Singleton base. Portable storage/declarations do not establish ARM ABI.
class BitmapDisplay : public IDisplay,
                      public Core::Portable::Singleton<BitmapDisplay> {
public:
  BitmapDisplay();
  ~BitmapDisplay() override;
  virtual int getScreenWidth() const;
  virtual int getScreenHeight() const;
  virtual bool getPixel(int x, int y) const;
  virtual void setPixel(int x, int y, bool value);
  void _fillRect(int x, int y, int width, int height, int mode);
  void _fillRect(const Rectangle &rectangle, int mode);
  virtual void fillRect(const Rectangle &rectangle);
  virtual void eraseRect(const Rectangle &rectangle);
  virtual void invertRect(const Rectangle &rectangle);
  virtual int setPen(int pen);
  virtual int setTextColor(int color);
  virtual void moveTo(int x, int y);
  virtual void getPos(int &x, int &y) const;
  void setPort(IPanelIO *port);
  void update(bool force);
  virtual char *getBitmapData() const;
  virtual void copyBits(char *destination, const char *source,
                        const Point &point, const Rectangle &rectangle);
  void copyBits(const char *source, const Point &point,
                const Rectangle &rectangle);
  void getScreenBits(char *destination, const Point &point,
                     const Rectangle &rectangle);
  void clear();
  virtual int getCharHeight() const;
  virtual int getTextBoxHeight() const;
  virtual int pixelLength(const char *);
  virtual void drawText(int, int, const char *, int, Rectangle *);
  virtual void drawString(const char *, int, Rectangle *);

private:
  friend struct presonus::surface_panel_port::BitmapDrawingAccess;
  std::array<std::uint8_t, 3072> bitmap_{};
  int pen_ = 0;
  int textColor_ = 0;
  int x_ = 0;
  int y_ = 0;
  bool textDirty_ = true;
  Core::Threads::Lock textLock_;
  IPanelIO *port_ = nullptr;
  std::array<std::uint8_t, 1540> lastSent_{};
};
} // namespace Presonus::Panel

namespace presonus::surface_panel_port {
// Independent port/fixture access, not original class methods.
struct BitmapDrawingAccess {
  static auto &lock(Presonus::Panel::BitmapDisplay &display) {
    return display.textLock_;
  }
  static auto &lastSent(Presonus::Panel::BitmapDisplay &display) {
    return display.lastSent_;
  }
  static void dirty(Presonus::Panel::BitmapDisplay &display, bool value) {
    display.textDirty_ = value;
  }
  static auto *port(const Presonus::Panel::BitmapDisplay &display) {
    return display.port_;
  }
  static bool textDirty(const Presonus::Panel::BitmapDisplay &display) {
    return display.textDirty_;
  }
  static auto &bitmap(Presonus::Panel::BitmapDisplay &display) {
    return display.bitmap_;
  }
  static void setState(Presonus::Panel::BitmapDisplay &display, int pen,
                       int color, int x, int y) {
    display.pen_ = pen;
    display.textColor_ = color;
    display.x_ = x;
    display.y_ = y;
  }
  static std::array<int, 4>
  state(const Presonus::Panel::BitmapDisplay &display) {
    return {display.pen_, display.textColor_, display.x_, display.y_};
  }
};
} // namespace presonus::surface_panel_port
