#include "presonus/ColorButton.hpp"

#include <cstdio>
#include <string_view>

namespace {
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;

template <class Base> class ObservedButton final : public Base {
public:
  using Base::Base;

  void invalidate(Core::RectRef rectangle) override {
    std::printf("invalidate %d %d %d %d %d\n", rectangle.left, rectangle.top,
                rectangle.right, rectangle.bottom, this->isEnabled());
  }
};
} // namespace

template <bool Provider> int run() {
  NumericParam primary(ParamInfo{});
  NumericParam other(ParamInfo{});

  for (const bool colorIsPrimary : {false, true}) {
    const auto size = Core::Rect(5, 7, 20, 29);
    ObservedButton<Core::Portable::Control> provider(size, &primary);
    ObservedButton<ColorButton> implementation(
        size, &primary, colorIsPrimary ? &primary : &other);
    auto &button = Provider
                       ? static_cast<Core::Portable::Control &>(provider)
                       : static_cast<Core::Portable::Control &>(implementation);
    for (const int message : {Parameter::kBeginEdit, Parameter::kEdit,
                              Parameter::kChanged, Parameter::kRangeChanged}) {
      for (const bool notifyPrimary : {false, true}) {
        primary.enable(false);
        button.enable(true);
        std::printf("case %d %d %d\n", colorIsPrimary, message, notifyPrimary);
        button.paramChanged(notifyPrimary ? &primary : &other, message);
        if constexpr (Provider) {
          std::puts("direct");
          provider.Core::Portable::View::invalidate();
        }
        std::printf("enabled %d\n", button.isEnabled());
      }
    }
  }
  return 0;
}

int main(int argc, char **argv) {
  if (argc == 1)
    return run<false>();
  if (argc == 2 && std::string_view(argv[1]) == "--provider")
    return run<true>();
  return 2;
}
