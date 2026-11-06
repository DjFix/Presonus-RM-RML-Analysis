#include "core/portable/gui/coregraphics.h"
#include "presonus/FocusHelperButton.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <functional>
#include <iostream>
#include <memory>
#include <vector>
using namespace Core;
using namespace Core::Portable;
struct RawParam : NumericParam {
  using NumericParam::NumericParam;
  float raw = 0;
  mutable int reads = 0;
  std::function<void()> onEnd;
  void endEdit() override {
    if (onEnd)
      onEnd();
    NumericParam::endEdit();
  }
  ParamValue getValue() const override {
    ++reads;
    return raw;
  }
};
struct Paint : Graphics {
  int fills = 0;
  bool setOrigin(PointRef) override { return true; }
  bool setClip(RectRef) override { return true; }
  int setMode(int m) override { return m; }
  bool fillRect(RectRef, ColorRef) override {
    ++fills;
    return true;
  }
  bool drawRect(RectRef, ColorRef) override { return true; }
  bool drawLinearGradient(PointRef, PointRef, ColorRef, ColorRef,
                          Direction) override {
    return true;
  }
  bool drawLine(PointRef, PointRef, ColorRef) override { return true; }
  bool drawString(RectRef, CStringPtr, ColorRef, CStringPtr, int) override {
    return true;
  }
  bool drawMultiLineString(RectRef, CStringPtr, ColorRef, CStringPtr,
                           int) override {
    return true;
  }
  int getStringWidth(CStringPtr, CStringPtr) const override { return 0; }
  bool drawBitmap(PointRef, Bitmap &, RectRef, const BitmapMode *) override {
    return true;
  }
  const BitmapFont *getFont(CStringPtr) const override { return nullptr; }
};
struct Probe : Presonus::FocusHelperButton {
  using FocusHelperButton::FocusHelperButton;
  mutable int roots = 0;
  bool observeRoots = false;
  void active(bool b) { active_ = b; }
  void expireEdit() { endEditTime = 1e-100; }
  // Uses the real hierarchy; records the original virtual boundary.
  RootView *getRootView() const override {
    if (observeRoots) {
      assert(!portableActive());
      ++roots;
    }
    return FocusHelperButton::getRootView();
  }
};
struct Child : View {
  RootView *routedRoot = nullptr;
  RootView *getRootView() const override { return routedRoot; }
  Probe *button;
  int id;
  std::vector<int> *events;
  Child(Probe *b, int i, std::vector<int> *e) : button(b), id(i), events(e) {}
  void onFocus(bool state) override {
    assert(!button->portableActive());
    events->push_back(state ? id + 1 : -id - 1);
    View::onFocus(state);
  }
};
struct Root : RootView {
  std::vector<View *> requests;
  void setFocusView(View *v) override {
    requests.push_back(v);
    RootView::setFocusView(v);
  }
};
struct InvalidView : View {
  void *castTo(TypeID) override { return nullptr; }
};
static ParamInfo info() {
  ParamInfo i{};
  i.type = ParamInfo::kFloat;
  i.minValue = -2147483648.f;
  i.maxValue = 2147483648.f;
  return i;
}
static void regressions() {
  auto i = info();
  RawParam p(i);
  Probe b(Rect(0, 0, 20, 20), &p, 1);
  assert(!b.portableActive() && std::strcmp(b.portableViewName(), "") == 0);
  DefaultAllocatedAttributes a;
  a.set("viewName", "target");
  b.setAttributes(a);
  assert(b.portableViewName() == a.getString("viewName"));
  a.set("viewName", "other");
  b.setAttributes(a);
  assert(b.portableViewName() == a.getString("viewName"));
  DefaultAllocatedAttributes empty;
  b.setAttributes(empty);
  assert(std::strcmp(b.portableViewName(), "") == 0);
  b.setValue(1);
  p.raw = 1;
  p.changed();
  assert(b.portableActive());
  b.active(false);
  p.raw = 0;
  p.changed();
  assert(!b.portableActive());
  p.enable(false);
  p.changed();
  assert(!b.isEnabled());
  p.enable(true);
  p.changed();
  assert(b.isEnabled());
  // An expired real provider edit ends while active is still true; only then
  // does restoreFocus clear it. This independently checks the base call order.
  b.active(true);
  p.onEnd = [&] { assert(b.portableActive()); };
  p.beginEdit();
  b.expireEdit();
  b.onIdle();
  assert(!p.isEditing() && !b.portableActive());
  p.onEnd = {};
}
int main() {
  regressions();
  int mode, value, active, msg, parent, hasRoot, n;
  std::uint32_t bits;
  while (std::cin >> mode >> bits >> value >> active >> msg >> parent >>
         hasRoot >> n) {
    std::vector<int> names(n);
    for (int &x : names)
      std::cin >> x;
    auto i = info();
    RawParam p(i), other(i);
    std::memcpy(&p.raw, &bits, 4);
    // An unbound incoming parameter still activates on matching value.
    Probe b(Rect(0, 0, 20, 20), mode == 1 ? &p : &other, value);
    b.active(active);
    int frames = 0;
    std::vector<int> focused;
    if (mode == 0) {
      b.paramChanged(&p, msg);
      assert(p.reads == (msg == 3 ? 1 : 0));
    } else if (mode == 1) {
      b.enable(msg != 0);
      Paint paint;
      DrawEvent event(paint, Rect(0, 0, 20, 20));
      b.draw(event);
      // Real Button::draw supplies one background fill. Real ThemePainter
      // supplies four focus edge fills for the extra FocusHelper frame.
      assert(paint.fills == 1 || paint.fills == 5);
      frames = (paint.fills - 1) / 4;
    } else {
      Root root;
      Root childRoot;
      ContainerView container;
      View plain;
      InvalidView invalid;
      DefaultAllocatedAttributes a;
      a.set("viewName", "target");
      b.setAttributes(a);
      if (hasRoot)
        root.addView(&container);
      std::vector<int> events;
      std::vector<std::unique_ptr<Child>> children;
      for (int j = 0; j < n; ++j) {
        children.emplace_back(std::make_unique<Child>(&b, j, &events));
        // Every child reports a different actual RootView from the button.
        children.back()->routedRoot = &childRoot;
        children.back()->setName(names[j] ? "target" : "other");
        container.addView(children.back().get());
      }
      if (parent == 2)
        container.addView(&b);
      else if (parent == 1)
        b.setParent(&invalid);
      else if (parent == 3)
        b.setParent(&plain);
      b.observeRoots = true;
      if (mode == 2)
        b.restoreFocus();
      else
        b.onIdle();
      assert(childRoot.requests.empty() && childRoot.getFocusView() == nullptr);
      for (auto *v : root.requests) {
        for (int j = 0; j < n; ++j)
          if (v == children[j].get())
            focused.push_back(j);
      }
      if (!focused.empty()) {
        assert(root.getFocusView() == children[focused.back()].get());
        std::vector<int> expectedEvents;
        for (std::size_t j = 0; j < focused.size(); ++j) {
          if (j)
            expectedEvents.push_back(-focused[j - 1] - 1);
          expectedEvents.push_back(focused[j] + 1);
        }
        assert(events == expectedEvents);
      }
      b.observeRoots = false;
      root.setFocusView(nullptr);
      if (parent == 2)
        container.removeView(&b);
      else
        b.setParent(nullptr);
      for (auto &child : children)
        container.removeView(child.get());
      if (hasRoot)
        root.removeView(&container);
    }
    std::cout << int(b.portableActive()) << ' ' << frames << ' ' << b.roots;
    for (int x : focused)
      std::cout << ' ' << x;
    std::cout << '\n';
  }
}
