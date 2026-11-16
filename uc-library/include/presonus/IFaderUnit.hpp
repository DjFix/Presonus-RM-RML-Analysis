#pragma once
namespace Presonus {
// Partial portable interface. Original other virtual methods, construction,
// inheritance and ARM layout remain unresolved.
class IFaderUnit {
public:
  struct SourcePortTag {};
  explicit IFaderUnit(SourcePortTag) noexcept {}
  virtual ~IFaderUnit();
};
} // namespace Presonus
