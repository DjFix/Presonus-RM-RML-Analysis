#pragma once

namespace presonus::avb {
// Independent names for observed constructor values, not recovered field names.
struct ListenerState {
  unsigned char identifierByte;
  unsigned long long identifier;
  unsigned long long streamKey;
  unsigned short suffix;
  int integerWord;
};
struct TalkerState {
  unsigned char identifierByte;
  int integerWord;
};
} // namespace presonus::avb

namespace Presonus::AVB {
// Portable state subsets; no complete original layout or ownership claim.
class AvbListener {
public:
  AvbListener(unsigned char identifierByte, unsigned long long identifier,
              unsigned short suffix, int integerWord);
  ~AvbListener();

  // Original body is a constant-one stub. Caller uses its truth value.
  // bool is a portable choice, not proof of the original return spelling.
  bool update(unsigned char first, unsigned char second, unsigned char third);
  presonus::avb::ListenerState inspectState() const { return state_; }

private:
  presonus::avb::ListenerState state_;
};

class AvbTalker {
public:
  AvbTalker(unsigned char identifierByte, int integerWord);
  ~AvbTalker();
  bool update(unsigned char first, unsigned char second);
  presonus::avb::TalkerState inspectState() const { return state_; }

private:
  presonus::avb::TalkerState state_;
};
} // namespace Presonus::AVB
