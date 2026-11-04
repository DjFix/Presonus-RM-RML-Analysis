#include "presonus/IDAWTimeInfo.hpp"
namespace Presonus {
IDAWTimeInfo::~IDAWTimeInfo() {
  // Opaque base dispatch identity observed in CS18AI 13840 ELF
  // 304c6cd1...; this value is not a callable host address or an ABI claim.
  dispatchState_.identity = 1691928;
}
} // namespace Presonus
