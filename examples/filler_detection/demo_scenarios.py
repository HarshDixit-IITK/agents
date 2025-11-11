"""
Demo scenarios for testing filler detection.

This script demonstrates different scenarios for testing the filler detection
functionality without needing a live room connection.
"""

import logging

from filler_detector import FillerDetectionConfig, FillerDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("demo")


class DemoScenarios:
    """Demonstration of various filler detection scenarios."""
    
    def __init__(self):
        """Initialize demo with various configurations."""
        self.configs = {
            "default": FillerDetectionConfig(),
            "strict": FillerDetectionConfig(
                min_real_words=2,
                confidence_threshold=0.7,
            ),
            "permissive": FillerDetectionConfig(
                min_real_words=1,
                confidence_threshold=0.3,
            ),
            "multilingual": FillerDetectionConfig(
                ignored_words=[
                    "uh", "um", "hmm",  # English
                    "haan", "achha",  # Hindi
                    "este", "pues",  # Spanish
                    "嗯", "啊",  # Chinese
                ]
            ),
        }
    
    def run_scenario(self, name: str, config_name: str, test_cases: list):
        """Run a test scenario with given configuration."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Scenario: {name}")
        logger.info(f"Configuration: {config_name}")
        logger.info(f"{'='*60}\n")
        
        detector = FillerDetector(self.configs[config_name])
        
        for test in test_cases:
            transcript = test["text"]
            agent_state = test.get("agent_state", "speaking")
            confidence = test.get("confidence", None)
            expected = test.get("expected", "")
            
            result = detector.analyze_transcript(
                text=transcript,
                confidence=confidence,
                agent_state=agent_state,
            )
            
            status = "✅" if result.should_interrupt == expected else "❌"
            
            logger.info(f"{status} Transcript: '{transcript}'")
            logger.info(f"   Agent State: {agent_state}")
            logger.info(f"   Is Filler Only: {result.is_filler_only}")
            logger.info(f"   Should Interrupt: {result.should_interrupt}")
            logger.info(f"   Detected Fillers: {result.detected_fillers}")
            logger.info(f"   Real Word Count: {result.real_word_count}")
            logger.info(f"   Reason: {result.reason}")
            if expected:
                logger.info(f"   Expected: {expected}, Got: {result.should_interrupt}")
            logger.info("")
    
    def scenario_1_basic_fillers(self):
        """Scenario 1: Basic filler detection while agent is speaking."""
        test_cases = [
            {
                "text": "uh",
                "agent_state": "speaking",
                "expected": False,
            },
            {
                "text": "um hmm",
                "agent_state": "speaking",
                "expected": False,
            },
            {
                "text": "uh uh uh",
                "agent_state": "speaking",
                "expected": False,
            },
        ]
        
        self.run_scenario(
            "Basic Filler Words (Agent Speaking)",
            "default",
            test_cases,
        )
    
    def scenario_2_real_interruptions(self):
        """Scenario 2: Real interruptions that should stop the agent."""
        test_cases = [
            {
                "text": "wait",
                "agent_state": "speaking",
                "expected": True,
            },
            {
                "text": "stop",
                "agent_state": "speaking",
                "expected": True,
            },
            {
                "text": "no not that",
                "agent_state": "speaking",
                "expected": True,
            },
            {
                "text": "hold on",
                "agent_state": "speaking",
                "expected": True,
            },
        ]
        
        self.run_scenario(
            "Real Interruptions (Agent Speaking)",
            "default",
            test_cases,
        )
    
    def scenario_3_mixed_input(self):
        """Scenario 3: Mixed filler and real words."""
        test_cases = [
            {
                "text": "uh wait",
                "agent_state": "speaking",
                "expected": True,
            },
            {
                "text": "um actually no",
                "agent_state": "speaking",
                "expected": True,
            },
            {
                "text": "hmm okay stop",
                "agent_state": "speaking",
                "expected": True,
            },
        ]
        
        self.run_scenario(
            "Mixed Filler and Real Words",
            "default",
            test_cases,
        )
    
    def scenario_4_agent_quiet(self):
        """Scenario 4: Fillers when agent is quiet (should be registered)."""
        test_cases = [
            {
                "text": "uh",
                "agent_state": "listening",
                "expected": True,
            },
            {
                "text": "hmm",
                "agent_state": "listening",
                "expected": True,
            },
            {
                "text": "umm okay",
                "agent_state": "listening",
                "expected": True,
            },
        ]
        
        self.run_scenario(
            "Fillers When Agent Quiet",
            "default",
            test_cases,
        )
    
    def scenario_5_confidence_threshold(self):
        """Scenario 5: Low confidence transcripts."""
        test_cases = [
            {
                "text": "uh maybe",
                "agent_state": "speaking",
                "confidence": 0.3,
                "expected": False,  # Below threshold
            },
            {
                "text": "uh maybe",
                "agent_state": "speaking",
                "confidence": 0.8,
                "expected": True,  # Above threshold
            },
        ]
        
        self.run_scenario(
            "Confidence Threshold Filtering",
            "default",
            test_cases,
        )
    
    def scenario_6_multilingual(self):
        """Scenario 6: Multilingual filler words."""
        test_cases = [
            {
                "text": "haan",
                "agent_state": "speaking",
                "expected": False,
            },
            {
                "text": "achha",
                "agent_state": "speaking",
                "expected": False,
            },
            {
                "text": "este pues",
                "agent_state": "speaking",
                "expected": False,
            },
            {
                "text": "嗯 啊",
                "agent_state": "speaking",
                "expected": False,
            },
            {
                "text": "haan wait",
                "agent_state": "speaking",
                "expected": True,
            },
        ]
        
        self.run_scenario(
            "Multilingual Fillers",
            "multilingual",
            test_cases,
        )
    
    def scenario_7_strict_config(self):
        """Scenario 7: Strict configuration (requires 2+ real words)."""
        test_cases = [
            {
                "text": "uh stop",
                "agent_state": "speaking",
                "expected": False,  # Only 1 real word
            },
            {
                "text": "uh please stop",
                "agent_state": "speaking",
                "expected": True,  # 2 real words
            },
            {
                "text": "wait one second",
                "agent_state": "speaking",
                "expected": True,  # 3 real words
            },
        ]
        
        self.run_scenario(
            "Strict Configuration (min 2 words)",
            "strict",
            test_cases,
        )
    
    def run_all_scenarios(self):
        """Run all demonstration scenarios."""
        logger.info("\n" + "="*60)
        logger.info("FILLER DETECTION DEMO SCENARIOS")
        logger.info("="*60)
        
        self.scenario_1_basic_fillers()
        self.scenario_2_real_interruptions()
        self.scenario_3_mixed_input()
        self.scenario_4_agent_quiet()
        self.scenario_5_confidence_threshold()
        self.scenario_6_multilingual()
        self.scenario_7_strict_config()
        
        logger.info("\n" + "="*60)
        logger.info("DEMO COMPLETE")
        logger.info("="*60)
    
    def show_statistics(self):
        """Show statistics for each configuration."""
        logger.info("\n" + "="*60)
        logger.info("CONFIGURATION DETAILS")
        logger.info("="*60 + "\n")
        
        for name, config in self.configs.items():
            logger.info(f"Configuration: {name}")
            logger.info(f"  Ignored Words ({len(config.ignored_words)}): {config.ignored_words[:10]}...")
            logger.info(f"  Confidence Threshold: {config.confidence_threshold}")
            logger.info(f"  Min Real Words: {config.min_real_words}")
            logger.info(f"  Case Sensitive: {config.case_sensitive}")
            logger.info(f"  Whole Word Match: {config.whole_word_match}")
            logger.info("")


def main():
    """Run the demo scenarios."""
    demo = DemoScenarios()
    
    # Show configuration details
    demo.show_statistics()
    
    # Run all scenarios
    demo.run_all_scenarios()


if __name__ == "__main__":
    main()

