#include "presonus/DisplayCommandList.hpp"
#include "presonus/LcdView.hpp"
#include "presonus/surface/DisplayManager.hpp"
#include <new>
namespace Presonus {
DisplayManager *DisplayManager::theInstance = nullptr;
DisplayManager::DisplayManager() = default;

DisplayManager::DisplayManager(const DisplaySpecification &specification)
    : DisplayManager() {
  using Core::Portable::RootViewBase;
  specification_ = specification;
  theInstance = this;

  const auto appendView = [this](Core::RectRef size,
                                 Core::BitmapPixelFormat format,
                                 RootViewBase::RenderMode mode) {
    auto view = std::make_unique<LcdView>(size, format, mode);
    if (!ownedViews_.add(view.get()))
      throw std::bad_alloc();
    return view.release();
  };

  root_ =
      appendView(Core::Rect(0, 0, specification_.width, specification_.height),
                 specification_.pixelFormat,
                 specification_.useFlipRoot ? RootViewBase::kFlipMode
                                            : RootViewBase::kOffscreenMode);
  const auto extraMode = specification_.useExternalExtras
                             ? RootViewBase::kExternalMode
                             : RootViewBase::kOffscreenMode;
  const Core::Rect extraSize(0, 0, specification_.extraWidth,
                             specification_.extraHeight);
  for (int i = 0; i < specification_.extraCount; ++i)
    appendView(extraSize, Core::kBitmapMonochrome, extraMode);

  if (specification_.useExternalExtras)
    ownedCommands_ = std::make_unique<DisplayCommandList>();
}

DisplayManager::~DisplayManager() {
  theInstance = nullptr;
  const int count = ownedViews_.count();
  for (int i = 0; i < count; ++i)
    delete ownedViews_.at(i);
  ownedCommands_.reset();
  ::operator delete(ownedCommandStorage_);
}
DisplayManager *DisplayManager::getInstance() { return theInstance; }
} // namespace Presonus
