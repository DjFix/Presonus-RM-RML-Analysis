#include "core/portable/coreparaminfo.h"
#include "presonus/PotControl.hpp"
#include <cassert>
#include <iostream>
using namespace Core;
using namespace Core::Portable;
namespace {
struct Param : NumericParam {
  mutable int enabledCalls = 0;
  explicit Param(const ParamInfo &info) : NumericParam(info) {}
  bool isEnabled() const override {
    ++enabledCalls;
    return false;
  }
};
struct Root : RootView {
  int focusCalls = 0;
  Root() : RootView(Rect(0, 0, 64, 64)) {}
  void setFocusView(View *v) override {
    ++focusCalls;
    RootView::setFocusView(v);
  }
};
struct Pot : Presonus::PotControl {
  mutable int rootCalls = 0;
  int frameCalls = 0;
  Param *observed = nullptr;
  bool providerBeforeFrames = false;
  Root *root = nullptr;
  Pot() : PotControl(Rect(0, 0, 16, 16)) {}
  RootView *getRootView() const override {
    ++rootCalls;
    return root;
  }
  void changeFrames() override {
    ++frameCalls;
    providerBeforeFrames =
        observed && observed->enabledCalls == 1 && !isEnabled();
  }
  void bind(Parameter *p) { parameter = p; }
};
} // namespace
int main() {
  static_assert((kGestureSingleTap | kGesturePriorityNormal) == 0x02000004);
  static_assert((kGestureDoubleTap | kGesturePriorityNormal) == 0x02000005);
  const ParamInfo info =
      PARAM_FLOAT(1, "Gain", 0, 1, 0.5f, 0.1f, nullptr, 0, 0, 0);
  int mode, flags, a, b, d;
  while (std::cin >> mode >> flags >> a >> b >> d) {
    Param p(info), other(info);
    Root root;
    Pot pot;
    pot.bind(b ? &p : nullptr);
    pot.observed = &p;
    pot.portableBindDrawState(0, -1, 4, flags);
    pot.root = d ? &root : nullptr;
    if (mode == 0) {
      pot.paramChanged(d == 0 ? nullptr : d == 1 ? &p : &other, a);
      const bool matching = b && d == 1 && a == Parameter::kChanged;
      assert(p.enabledCalls == int(matching));
      if (matching) {
        assert(!pot.isEnabled());
        assert(pot.providerBeforeFrames);
      }
      std::cout << pot.frameCalls;
    } else if (mode == 1) {
      FixedSizeVector<int, 8> v;
      for (int i = 0; i < a; ++i)
        v.add(100 + i);
      pot.getHandledGestures(v, Point(-100, 271));
      std::cout << v.count();
      for (int i = 0; i < v.count(); ++i)
        std::cout << ' ' << v[i];
    } else {
      int user = 123;
      const bool result = pot.onGestureInput(GestureEvent(user, a));
      const bool editing = TextInput::isEditing(&root);
      assert(user == 123);
      const int appFocusCalls = root.focusCalls - int(editing);
      if (appFocusCalls)
        assert(root.getFocusView() == &pot);
      if (editing) {
        assert(root.getModalView());
        TextInput::stop(&root, true);
        assert(!root.getModalView());
        assert(!TextInput::isEditing(&root));
      }
      // A null root is an actual provider no-op after its assertion, so the
      // original observed text-start boundary projects to no modal creation.
      std::cout << result << ' ' << pot.rootCalls << ' ' << appFocusCalls << ' '
                << (editing ? 1 : 0);
      root.setFocusView(nullptr);
      pot.root = nullptr;
    }
    std::cout << '\n';
    pot.bind(nullptr);
  }
}
