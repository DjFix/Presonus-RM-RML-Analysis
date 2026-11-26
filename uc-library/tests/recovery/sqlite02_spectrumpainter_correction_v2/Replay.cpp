#include "presonus/SpectrumPainter.hpp"
#include "presonus/mixer_dsp/EQControl.hpp"

#include <bit>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

void printRect(Core::RectRef rect) {
  std::cout << ' ' << rect.left << ' ' << rect.top << ' ' << rect.right << ' '
            << rect.bottom;
}

Core::Rect readRect() {
  Core::Rect rect;
  std::cin >> rect.left >> rect.top >> rect.right >> rect.bottom;
  return rect;
}

struct ObservedGrid : Presonus::EQControl {
  ObservedGrid() : EQControl(presonus::dsp::EQControlBiquadPortTag{}) {
    bindPortableInterpolators(domain, domain, domain, domain);
  }

  int toXGridPixel(float frequency) const override {
    std::cout << "grid " << std::bit_cast<unsigned>(frequency) << '\n';
    return EQControl::toXGridPixel(frequency);
  }

  Core::LinearInterpolator domain{-64, 64};
};

struct ObservedRenderer : Core::Portable::ColorBitmapRenderer {
  explicit ObservedRenderer(Core::Portable::Bitmap &bitmap)
      : ColorBitmapRenderer(bitmap) {}

  bool fillRect(Core::RectRef rect, Core::ColorRef color) override {
    std::cout << "fill";
    printRect(rect);
    std::cout << ' ' << Core::uint32(color) << '\n';
    return ColorBitmapRenderer::fillRect(rect, color);
  }
};

struct DerivedPainter : Presonus::SpectrumPainter {
  explicit DerivedPainter(Presonus::IBackgroundGridProvider &grid)
      : SpectrumPainter(grid) {}
};

template <typename Painter> void run(Painter &painter) {
  Core::Portable::Bitmap canvas(128, 128, Core::kBitmapRGBAlpha);
  ObservedRenderer graphics(canvas);
  std::vector<float> amplitudes;
  std::vector<float> frequencies;
  Core::Rect bounds;
  std::cout << "last";
  printRect(painter.getLastDrawnRect());
  std::cout << "\nend\n";
  for (std::string command; std::cin >> command && command != "end";) {
    if (command == "bind") {
      unsigned count;
      std::cin >> count;
      amplitudes.resize(count);
      frequencies.resize(count);
      for (auto &amplitude : amplitudes)
        std::cin >> amplitude;
      for (auto &frequency : frequencies)
        std::cin >> frequency;
      painter.setData(amplitudes.data(), static_cast<int>(count),
                      frequencies.data());
    } else if (command == "init") {
      bounds = readRect();
      painter.init(bounds);
    } else if (command == "mutate" || command == "mutate_frequency") {
      unsigned index;
      float amplitude;
      std::cin >> index >> amplitude;
      auto &samples = command == "mutate" ? amplitudes : frequencies;
      samples.at(index) = amplitude;
    } else if (command == "calculate_bars" ||
               command == "calculate_next_draw_rect") {
      bounds = readRect();
      const auto result = command == "calculate_bars"
                              ? painter.calculateBars(bounds)
                              : painter.calculateNextDrawRect(bounds);
      std::cout << "result";
      printRect(result);
      std::cout << '\n';
    } else if (command == "paint") {
      const auto clip = readRect();
      Core::uint32 rgba;
      std::cin >> rgba;
      Core::Portable::Style style;
      style.setTextColor(Core::Color::fromInt(rgba));
      const Core::Portable::DrawEvent event(graphics, clip);
      painter.paint(bounds, event, style);
    } else {
      std::exit(1);
    }
    std::cout << "last";
    printRect(painter.getLastDrawnRect());
    std::cout << "\nend\n";
  }
}

} // namespace

int main() {
  Core::Rect borrowedBounds(2, -3, 7, 9);
  Presonus::SpectrumPainter borrowed(borrowedBounds);
  if (borrowed.getLastDrawnRect() != borrowedBounds)
    return 1;
  borrowedBounds.offset(-5, 7);
  if (borrowed.getLastDrawnRect() != borrowedBounds)
    return 1;

  for (std::string command, variant; std::cin >> command >> variant;) {
    if (command != "construct")
      return 1;
    ObservedGrid grid;
    if (variant == "complete_construct") {
      Presonus::SpectrumPainter painter(grid);
      run(painter);
    } else if (variant == "base_construct") {
      DerivedPainter painter(grid);
      run(painter);
    } else {
      return 1;
    }
  }
}
