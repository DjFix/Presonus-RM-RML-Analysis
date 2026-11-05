#include "presonus/LinkControl.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
using namespace Core;
using namespace Core::Portable;
class Recorder final : public Graphics {
public:
  int calls = 0, selected = 0;
  Point point;
  Rect rect;
  Bitmap *left = nullptr, *right = nullptr;
  bool setOrigin(PointRef) override { return false; }
  bool setClip(RectRef) override { return false; }
  int setMode(int) override { return 0; }
  bool fillRect(RectRef, ColorRef) override { return false; }
  bool drawRect(RectRef, ColorRef) override { return false; }
  bool drawLinearGradient(PointRef, PointRef, ColorRef, ColorRef,
                          Direction) override {
    return false;
  }
  bool drawLine(PointRef, PointRef, ColorRef) override { return false; }
  bool drawString(RectRef, CStringPtr, ColorRef, CStringPtr, int) override {
    return false;
  }
  bool drawMultiLineString(RectRef, CStringPtr, ColorRef, CStringPtr,
                           int) override {
    return false;
  }
  int getStringWidth(CStringPtr, CStringPtr) const override { return 0; }
  const BitmapFont *getFont(CStringPtr) const override { return nullptr; }
  bool drawBitmap(PointRef p, Bitmap &b, RectRef r,
                  const BitmapMode *mode) override {
    assert(!mode);
    ++calls;
    point = p;
    rect = r;
    selected = &b == left ? 1 : (&b == right ? 2 : 0);
    assert(selected);
    return true;
  }
};
class Link final : public Presonus::LinkControl {
public:
  Link() : LinkControl(Rect(0, 0, 20, 30)) {}
  void configure(Bitmap *l, Bitmap *r, Parameter *side) {
    leftImage = l;
    rightImage = r;
    rightSideParam = side;
  }
  ~Link() { rightSideParam = nullptr; }
};
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream f(argv[1]);
  assert(f);
  int linked, left, right, side, x, y, z, w, ox, oy, expected, px, py;
  unsigned count = 0;
  static const ParamInfo info = PARAM_TOGGLE(1, "state", 0, nullptr, 0);
  while (f >> linked >> left >> right >> side >> x >> y >> z >> w >> ox >> oy >>
         expected >> px >> py) {
    NumericParam lp(info), sp(info);
    lp.setValue(linked);
    sp.setValue(side);
    Bitmap l, r;
    Recorder g;
    g.left = &l;
    g.right = &r;
    {
      Link c;
      c.setParameter(linked < 0 ? nullptr : &lp);
      c.configure(left ? &l : nullptr, right ? &r : nullptr,
                  side < 0 ? nullptr : &sp);
      Rect rect(x, y, z, w);
      DrawEvent e(g, rect, Point(ox, oy));
      c.draw(e);
      assert(g.calls == (expected ? 1 : 0));
      assert(g.selected == expected);
      if (expected) {
        assert(g.point.x == px && g.point.y == py);
        assert(g.rect == rect);
      }
      c.setParameter(nullptr);
    }
    assert(!l.isReferenced() && !r.isReferenced());
    ++count;
  }
  assert(f.eof() && count);
  std::cout << count << " native fixture cases passed\n";
}
