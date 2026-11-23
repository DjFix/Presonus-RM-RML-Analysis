#include "presonus/panel/FillElement.hpp"
#include "presonus/surface_panel/BitmapDrawing.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>

namespace {
using namespace Presonus::Panel;

class ObservedBitmap final : public BitmapDisplay {
public:
  explicit ObservedBitmap(const FillElement &element) : element_(element) {}
  void fillRect(const Rectangle &rectangle) override {
    if (element_.needsToDraw())
      throw std::logic_error("fillRect called before dirty clear");
    rectangle_ = rectangle;
    ++count_;
    BitmapDisplay::fillRect(rectangle);
  }
  Rectangle rectangle_{};
  int count_ = 0;

private:
  const FillElement &element_;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 6)
    return 2;
  const int x = std::atoi(argv[1]), y = std::atoi(argv[2]);
  const int w = std::atoi(argv[3]), h = std::atoi(argv[4]);
  FillElement element(x, y, w, h, 9);
  ObservedBitmap bitmap(element);
  IDisplay &display = bitmap;
  element.render(display, std::atoi(argv[5]) != 0);
  for (int row = 0; row < bitmap.getScreenHeight(); ++row)
    for (int column = 0; column < bitmap.getScreenWidth(); ++column)
      if (bitmap.getPixel(column, row) !=
          (column >= x && column < x + w && row >= y && row < y + h))
        return 1;
  if (bitmap.count_ != 1)
    return 1;
  const auto &rect = bitmap.rectangle_;
  std::cout << rect.x << ' ' << rect.y << ' ' << rect.width << ' '
            << rect.height << ' ' << element.elementState().dirty << '\n';
}
