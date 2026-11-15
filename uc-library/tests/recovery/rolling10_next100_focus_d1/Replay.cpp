#include "presonus/FocusRestorer.hpp"
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
using namespace Core;
using namespace Core::Portable;
struct FocusView : View {
  using View::View;
  int changes = 0;
  void onFocus(bool state) override {
    ++changes;
    View::onFocus(state);
  }
};
static FocusView *makeView(const char *name, Rect rect) {
  auto *v = new FocusView(rect);
  v->wantsFocus(true);
  v->setName(std::string(63, 'x').c_str());
  v->setName(name);
  return v;
}
static int identify(View *v, View *target, View *other, View *replacement) {
  return !v ? 0 : v == target ? 1 : v == other ? 2 : v == replacement ? 3 : 9;
}
int main(int argc, char **argv) {
  const bool provider = argc > 1 && std::string(argv[1]) == "--provider";
  for (int c = 0; c < 11; ++c) {
    RootView rootA(Rect(0, 0, 400, 400)), rootB(Rect(0, 0, 400, 400));
    auto *container = new ContainerView(Rect(5, 7, 305, 307));
    auto *target = makeView("target", Rect(10, 10, 100, 100));
    auto *other = makeView("other", Rect(150, 150, 200, 200));
    container->addView(target);
    container->addView(other);
    if (c != 0)
      rootA.addView(container);
    if (c != 1 && c != 0)
      rootA.setFocusView(target);
    Presonus::FocusRestorer::FocusInfo reference;
    auto *initialRoot = container->getRootView();
    auto *initialFocus = initialRoot ? initialRoot->getFocusView() : nullptr;
    if (initialFocus)
      reference.setView(*initialFocus);
    std::unique_ptr<Presonus::FocusRestorer> restorer;
    if (!provider) {
      restorer = std::make_unique<Presonus::FocusRestorer>(*container);
      const auto &actual = restorer->sourcePortSnapshot();
      if (actual.observedState != reference.observedState)
        return 2;
      if (std::strcmp(actual.name.str(), reference.name.str()))
        return 3;
    }
    FocusView *replacement = nullptr;
    if (initialRoot)
      rootA.setFocusView(other);
    if (c >= 3 && c <= 6) {
      container->removeView(target);
      delete target;
      target = nullptr;
      replacement =
          makeView(c == 4 ? "wrong" : "target",
                   c == 5 ? Rect(11, 10, 100, 100) : Rect(10, 10, 100, 100));
      if (c == 6)
        replacement->wantsFocus(false);
      container->addView(replacement);
    }
    if (c == 7 || c == 10) {
      rootA.removeView(container);
      rootB.addView(container);
      rootB.setFocusView(other);
      if (c == 10)
        target->setName("changed");
    }
    if (c == 8)
      rootA.removeView(container);
    if (c == 9) {
      auto *wrong = makeView("wrong", Rect(10, 10, 100, 100));
      container->addView(wrong);
    }
    auto *currentRoot = container->getRootView();
    auto *before = currentRoot ? currentRoot->getFocusView() : nullptr;
    View *found = nullptr;
    if (reference.observedState[0] && currentRoot) {
      std::int32_t x, y;
      std::memcpy(&x, &reference.observedState[5], 4);
      std::memcpy(&y, &reference.observedState[6], 4);
      Presonus::FocusRestorer::FindFilter filter(reference);
      found = currentRoot->findView(Point(x, y), true, &filter);
    }
    int beforeTarget = target ? target->changes : 0;
    int beforeOther = other->changes;
    int beforeReplacement = replacement ? replacement->changes : 0;
    if (provider) {
      if (found)
        currentRoot->setFocusView(found);
      std::cout << c << ' ' << bool(initialRoot) << ' ' << bool(initialFocus)
                << ' ' << bool(currentRoot) << ' '
                << identify(found, target, other, replacement) << ' '
                << identify(before, target, other, replacement);
      for (auto x : reference.observedState)
        std::cout << ' ' << x;
      for (int i = 0; i < 32; ++i)
        std::cout << ' '
                  << (reference.observedState[0]
                          ? unsigned(static_cast<unsigned char>(
                                reference.name.getBuffer()[i]))
                          : 0U);
      std::cout << ' ' << (target ? target->changes - beforeTarget : 0) << ' '
                << other->changes - beforeOther << ' '
                << (replacement ? replacement->changes - beforeReplacement : 0)
                << '\n';
    } else {
      int ctorRoot, ctorFocus, ctorSet, dtorRoot, dtorFind, dtorSet;
      std::cin >> ctorRoot >> ctorFocus >> ctorSet >> dtorRoot >> dtorFind >>
          dtorSet;
      if (ctorRoot != 1 || ctorFocus != bool(initialRoot) ||
          ctorSet != bool(initialFocus) ||
          dtorRoot != bool(reference.observedState[0]) ||
          dtorFind != bool(reference.observedState[0] && currentRoot) ||
          dtorSet != bool(found))
        return 4;
      int expectedTarget, expectedOther, expectedReplacement;
      std::cin >> expectedTarget >> expectedOther >> expectedReplacement;
      restorer.reset();
      if ((target ? target->changes - beforeTarget : 0) != expectedTarget ||
          other->changes - beforeOther != expectedOther ||
          (replacement ? replacement->changes - beforeReplacement : 0) !=
              expectedReplacement)
        return 6;
      if (currentRoot &&
          currentRoot->getFocusView() != (found ? found : before))
        return 5;
      std::cout << c << ' '
                << identify(currentRoot ? currentRoot->getFocusView() : nullptr,
                            target, other, replacement)
                << '\n';
    }
    if (!container->getParent())
      delete container;
  }
}
