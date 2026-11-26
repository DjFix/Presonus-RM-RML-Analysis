#include "presonus/SLChannel.hpp"
#include <string>

namespace Presonus {
SLChannelBase::SLChannelBase() : UC::ClientComponent("") {}
SLChannelBase::~SLChannelBase() { delete linker_; }
void SLChannelBase::releaseSourcePortLinker() {
  delete linker_;
  linker_ = nullptr;
}
SLChannel::SLChannel() = default;
SLChannel::~SLChannel() = default;
bool SLChannelBase::isLinked() const { return linker_ && linker_->isLinked(); }
SLChannelBase *SLChannelBase::getLinkNeighbour() const {
  return linker_ ? &linker_->neighbour() : nullptr;
}
void SLChannelBase::getDefaultName(Core::CStringBuffer<128> &buffer) const {
  std::string name(buffer.str());
  name += defaultName_.str();
  if (name.size() > 127)
    name.resize(127);
  if (const auto aux = name.find("Aux"); aux != std::string::npos)
    name.replace(aux, 3, "Mix");
  if (name == "Ch")
    name += ". ";
  const int number = getNumber();
  if (name.rfind("Ch", 0) == 0 || name.rfind("Mix", 0) == 0)
    name += std::to_string(number);
  else if (name.rfind("FX", 0) == 0) {
    name += ' ';
    name += number >= 1 && number <= 4 ? "ABCD"[number - 1] : '?';
  }
  buffer = name.c_str();
}
} // namespace Presonus
