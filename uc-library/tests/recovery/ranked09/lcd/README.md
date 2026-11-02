Ranked trial 09 LCD stack work

The native oracle executes original popBackPage and pushBackPage ARM instructions
from CS18AI surface 13840 with exact ELF, section, range and hash checks. Its
60 cases cover counts 0..9, null and distinct page tokens. Original memory writes
and reads from Core::ConstVector<PageComponent*>::error are captured. That symbol
is independently verified as SHT_NOBITS; this fixture domain represents its
zero-initialized value, before application mutation. No Core body is recovered.

Ordinary original returns, class layout/inheritance and ARM ABI remain unresolved.
The pointer showPage packet requires missing syncPageParams callable context.

Stack operations explicitly select count-based mode. hasBackPage then reflects
actual CCL count, including a stored null page. The driver verifies legacy back
state before opt-in, ignores conflicting legacy values after opt-in, and checks
getCurrentPage priority remains next/current. The original trial08 driver and
80 fixtures replay unchanged with default legacy mode; required Application
operations remain pure virtual. No production dependency is replaced by a no-op.

The sealed syncPageParams expansion exposes child cast/page-tag/parameter
operations. PageComponent::getPageTag has no selected body or provider here;
PageComponent remains forward-declared. No pointer-overload reconstruction is
claimed and the existing integer path retains its meaningful application boundary.
