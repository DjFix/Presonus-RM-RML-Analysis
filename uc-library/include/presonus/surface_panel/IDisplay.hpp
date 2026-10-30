#pragma once
namespace Presonus::Panel {
class IPanelIO;
struct Point {
  int x;
  int y;
};
struct Rectangle {
  int x;
  int y;
  int width;
  int height;
};
// All23 original pure slots measured in both-role RTTI/vtables. Portable return
// declarations remain provisional; no invented virtual destructor slot.
class IDisplay {
public:
  virtual void setPort(IPanelIO *) = 0;
  virtual int getScreenWidth() const = 0;
  virtual int getScreenHeight() const = 0;
  virtual int getCharHeight() const = 0;
  virtual int getTextBoxHeight() const = 0;
  virtual void copyBits(char *, const char *, const Point &,
                        const Rectangle &) = 0;
  virtual void copyBits(const char *, const Point &, const Rectangle &) = 0;
  virtual void getScreenBits(char *, const Point &, const Rectangle &) = 0;
  virtual void clear() = 0;
  virtual void fillRect(const Rectangle &) = 0;
  virtual void eraseRect(const Rectangle &) = 0;
  virtual void invertRect(const Rectangle &) = 0;
  virtual void setPixel(int, int, bool) = 0;
  virtual bool getPixel(int, int) const = 0;
  virtual void drawText(int, int, const char *, int, Rectangle *) = 0;
  virtual void drawString(const char *, int, Rectangle *) = 0;
  virtual char *getBitmapData() const = 0;
  virtual int pixelLength(const char *) = 0;
  virtual int setPen(int) = 0;
  virtual int setTextColor(int) = 0;
  virtual void moveTo(int, int) = 0;
  virtual void getPos(int &, int &) const = 0;
  virtual void update(bool) = 0;

protected:
  ~IDisplay() =
      default; // Independent source lifetime helper, not historical slot.
};
} // namespace Presonus::Panel
