지금까지 논의한 **3GPP UE Power Class (HPUE 포함)**와 **Signaling(Single vs CA)**에 대한 기술적 내용을 전문가 관점에서 Total Summary 해드립니다.
요청하신 대로 허용 가능한 최대 깊이로, **Spec(TS 38.101, 38.331, 38.306)**과 실무적 로그 분석 내용을 망라하여 정리합니다.
[Master Report] 5G NR UE Power Class & Signaling Architecture
1. Power Class 정의 및 물리적 스펙 (TS 38.101-1)
가장 먼저, 단말(UE)이 송출할 수 있는 물리적인 최대 전력(Maximum Output Power)에 대한 정의입니다.
1.1. Power Class 분류
5G NR FR1 (Sub-6GHz) 기준, 주요 Power Class는 다음과 같습니다.
| Class | Max Power | Tolerance | 비고 (Use Case) |
|---|---|---|---|
| Class 1 | 31\text{ dBm} (1.25\text{ W}) | +2/-3\text{ dB} | FWA/CPE (고정형 라우터), 공공안전망 |
| Class 1.5 | 29\text{ dBm} (800\text{ mW}) | +2/-3\text{ dB} | 특정 대역(n41 등) 지원 단말 |
| Class 2 | 26\text{ dBm} (400\text{ mW}) | +2/-3\text{ dB} | HPUE (High Power UE). n78, n41, n77 등 TDD 커버리지 확장용 |
| Class 3 | 23\text{ dBm} (200\text{ mW}) | +2/-2\text{ dB} | Standard Handset. 모든 스마트폰의 기본값 (Default) |
1.2. HPUE (Class 2)의 필요성
 * TDD 특성: TDD는 시간 축을 나누어 쓰므로(Duty Cycle), FDD 대비 업링크 커버리지가 물리적으로 불리합니다.
 * 보상: 이를 보상하기 위해 출력을 3\text{ dB} (2배) 높여 셀 커버리지를 FDD 수준으로 맞추는 기술이 HPUE입니다.
2. RRC Signaling 구조 분석 (TS 38.331 & 38.306)
단말은 기지국에 자신이 지원하는 Power Class를 UE Capability Information 메시지를 통해 보고합니다.
2.1. 계층적 구조 (Hierarchy)
Power Class 정보는 **"기본 밴드 능력(Single)"**과 "CA 조합 능력(Combination)" 두 군데에 위치합니다.
(A) Per-Band Level (기초 체력)
가장 기본이 되는 설정입니다. 단말이 해당 주파수 밴드를 단독으로 사용할 때의 능력을 정의합니다.
 * 위치: UE-NR-Capability \rightarrow rf-Parameters \rightarrow supportedBandListNR \rightarrow BandNR
 * 필드명: pwrClass-r15
 * 로직:
   * Explicit: pwrClass-r15: pc2 \rightarrow Class 2 (HPUE) 동작.
   * Implicit (Default): 필드 부재(Absent) \rightarrow Class 3 (Standard) 동작.
(B) Band Combination Level (CA 응용 능력)
여러 밴드를 묶었을 때(CA), 여전히 고출력을 유지할 수 있는지 확인하는 설정입니다.
 * 위치: UE-NR-Capability \rightarrow rf-Parameters \rightarrow featureSetCombinations ... \rightarrow BandCombination
 * 필드명: powerClass-v1530
 * 로직:
   * 이 필드가 pc2로 설정되어 있으면, 해당 CA 조합(예: n1+n78) 상황에서도 n78 대역은 Class 2 출력을 지원한다는 의미입니다.
3. 핵심 논쟁: "Single Disable vs CA Enable" 가능성 검증
사용자님께서 제기하신 **"Single에서는 Class 3(Disable)인데, CA에서는 Class 2(Enable)인 상황"**에 대한 최종 분석입니다.
3.1. 물리적(RF Hardware) 관점: "불가능"
 * RF Path Loss: CA 모드는 다이플렉서/필터 추가 등으로 인해 Single 모드보다 RF 경로 손실(Insertion Loss)이 더 크거나 같습니다.
 * 결론: 경로 손실이 적은 Single 모드에서 26dBm을 못 내는 PA(전력증폭기)가, 손실이 더 큰 CA 모드에서 26dBm을 낸다는 것은 물리 법칙에 위배됩니다.
3.2. 스펙 문법(Syntax) 관점: "필드는 존재하나..."
 * TS 38.331 문법상 BandNR(Single)에는 pwrClass를 빼고, BandCombination(CA)에는 powerClass-v1530을 넣는 행위 자체는 가능합니다(Parsing 에러는 안 남).
3.3. 스펙 논리(Semantics) 관점: "구현 오류 (Defect)"
 * 상속(Inheritance) 원칙: CA 능력은 기본 밴드 능력의 부분집합(Subset)이거나 재확인(Re-confirmation)이어야 합니다. 기본 능력(Single)에 없는 파워를 CA에서 창조해낼 수는 없습니다.
 * 판정: 만약 로그가 그렇게 찍혔다면, 이는 단말 제조사의 NV Item 매핑 실수이거나 SW Logic Bug입니다. 네트워크는 이를 비정상 단말로 간주하거나, 보수적으로 Class 3로 동작시킬 가능성이 큽니다.
4. 실제 로그 분석 가이드 (Troubleshooting)
현업에서 로그를 분석하실 때 확인해야 할 체크리스트입니다.
Case 1: 정상적인 HPUE 지원 단말
/* 1. Single Band Config (BandNR) */
BandNR (n78) {
    pwrClass-r15: pc2  <-- [OK] 기본적으로 Class 2 지원 선언
}

/* 2. CA Combination Config (BandCombination) */
BandCombination (Item 15) {
    bandList: { ... n78 ... }
    powerClass-v1530: pc2 <-- [OK] CA 할 때도 Class 2 유지 가능 선언
}

\rightarrow 결과: Single, CA 모두 26dBm 동작.
Case 2: 사용자님이 발견한 "이상한" 케이스 (Bug 의심)
/* 1. Single Band Config (BandNR) */
BandNR (n78) {
    (pwrClass 필드 없음) <-- [Problem] 기본은 Class 3 (23dBm)라고 선언함
}

/* 2. CA Combination Config (BandCombination) */
BandCombination (Item 15) {
    bandList: { ... n78 ... }
    powerClass-v1530: pc2 <-- [Conflict] 근데 CA 하면 26dBm 된다고 함?
}

\rightarrow 분석결과: 물리적으로 Single에서 안 되는 게 CA에서 될 리가 없으므로, **"Single 설정 누락(Missing Config)"**으로 판단됩니다.
\rightarrow 조치: 단말 제조사에 BandNR 섹션의 pwrClass-r15 필드 누락 버그 리포팅 필요.
5. 결론 및 요약 (Takeaway)
 * UE Power Class는 단말의 최대 출력을 정의하며, **Class 2(HPUE)**는 TDD 대역(n78 등)의 커버리지 핵심 기술이다.
 * 이 정보는 RRC UECapabilityInformation 메시지의 BandNR (Single)과 BandCombination (CA) 두 곳에 필드가 존재한다.
 * 3GPP 표준 및 RF 물리 원칙상, Single 모드에서 지원하지 않는 고출력을 CA 모드에서만 지원하는 것은 논리적/물리적으로 불가능하다.
 * 로그에서 그런 현상이 보인다면, 이는 CA 전용 기능이 켜진 것이 아니라 **기본 Single 설정(BandNR)에서의 파라미터 누락(실수)**일 확률이 99% 이상이다.
이 정리를 통해 3GPP 스펙 구조와 로그 현상에 대한 명확한 기준을 잡으셨기를 바랍니다.
