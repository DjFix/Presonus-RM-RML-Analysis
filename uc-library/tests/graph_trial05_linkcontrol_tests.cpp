#include "core/portable/coreattributes.h"
#include "presonus/LinkControl.hpp"
#include <cstdlib>
#include <iostream>
struct Probe : Presonus::LinkControl {
  int invalidations = 0;
  using Control::invalidate;
  void invalidate(Core::RectRef) override { ++invalidations; }
  void seed(Core::Portable::Parameter *p) { rightSideParam = p; }
  Core::Portable::Parameter *right() const { return rightSideParam; }
  bool imagesEmpty() const {
    return !leftImage.isValid() && !rightImage.isValid();
  }
};
int main(int argc, char **argv) {
  if (argc != 7)
    return 2;
  int op = std::atoi(argv[1]), old = std::atoi(argv[2]),
      next = std::atoi(argv[3]), msg = std::atoi(argv[4]);
  float value = std::strtof(argv[5], nullptr);
  Core::Portable::ParamInfo info{};
  info.defaultValue = value;
  Core::Portable::NumericParam a(info), b(info);
  Core::Portable::Parameter *ps[] = {nullptr, &a, &b};
  Probe p;
  p.seed(ps[old]);
  int result = -1;
  if (op == 1) {
    p.setParameter(ps[old]);
    result = p.isLinked();
  }
  if (op == 2)
    result = p.isRightSideOfLink();
  if (op == 3)
    p.setRightSideParam(ps[next]);
  if (op == 4)
    p.paramChanged(ps[next], msg);
  if (op == 5) {
    Core::Portable::Attributes attrs(
        Core::Portable::AttributeAllocator::getDefault());
    p.setAttributes(attrs);
    result = p.imagesEmpty();
  }
  int right = p.right() == nullptr ? 0 : p.right() == &a ? 1 : 2;
  std::cout << result << " " << right << " " << p.invalidations << "\n";
  // Lifetime is not reconstructed: explicitly disconnect test-owned observers.
  if (op == 3)
    p.setRightSideParam(nullptr);
  p.seed(nullptr);
  p.setParameter(nullptr);
}
