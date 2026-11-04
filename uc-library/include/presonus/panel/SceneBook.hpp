#pragma once
#include "presonus/panel/Book.hpp"
#include <cstdint>
namespace Presonus::Panel {
// Partial portable constructor model. Composition and opaque dispatch identity
// are independent storage, not original inheritance or virtual layout.
class SceneBook {
public:
  explicit SceneBook(int initialValue);
  const Book &bookState() const { return book_; }
  std::uint32_t opaqueDispatchIdentity() const { return dispatchIdentity_; }

private:
  Book book_;
  std::uint32_t dispatchIdentity_;
};
} // namespace Presonus::Panel
