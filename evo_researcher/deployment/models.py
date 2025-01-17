import pytz
from decimal import Decimal
from datetime import datetime, timedelta
from evo_researcher.benchmark.agents import EvoAgent, OlasAgent, EmbeddingModel
from prediction_market_agent_tooling.benchmark.agents import AbstractBenchmarkedAgent
from prediction_market_agent_tooling.markets.agent_market import AgentMarket
from prediction_market_agent_tooling.markets.manifold.manifold import ManifoldAgentMarket
from prediction_market_agent_tooling.markets.omen.omen import OmenAgentMarket
from prediction_market_agent_tooling.deploy.agent import DeployableAgent, BetAmount
from prediction_market_agent_tooling.markets.betting_strategies import minimum_bet_to_win
from prediction_market_agent_tooling.markets.manifold.api import get_manifold_bets, get_authenticated_user, get_manifold_market
from prediction_market_agent_tooling.markets.omen.omen import get_omen_bets
from prediction_market_agent_tooling.tools.utils import should_not_happen
from prediction_market_agent_tooling.config import APIKeys


class DeployableAgentER(DeployableAgent):
    agent: AbstractBenchmarkedAgent

    def recently_betted(self, market: AgentMarket) -> bool:
        # TODO: Replace with utcnow from PMAT once it's merged and released.
        start_time = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(hours=48)
        keys = APIKeys()
        recently_betted_questions = [get_manifold_market(b.contractId).question for b in get_manifold_bets(
            user_id=get_authenticated_user(keys.manifold_api_key.get_secret_value()).id,
            start_time=start_time,
            end_time=None,
        )] if isinstance(market, ManifoldAgentMarket) else [b.title for b in get_omen_bets(
            better_address=keys.bet_from_address,
            start_time=start_time,
            end_time=None,
        )] if isinstance(market, OmenAgentMarket) else should_not_happen(f"Uknown market: {market}")
        return market.question in recently_betted_questions

    def pick_markets(self, markets: list[AgentMarket]) -> list[AgentMarket]:
        """
        Testing mode: Pick only one predictable market or nothing.
        """
        for market in markets:
            print(f"Looking if we recently bet on '{market.question}'.")
            if self.recently_betted(market):
                print("Recently betted, skipping.")
                continue
            print(f"Verifying market predictability for '{market.question}'.")
            if self.agent.is_predictable(market.question):
                print(f"Market '{market.question}' is predictable.")
                return [market]
        return []
    
    def calculate_bet_amount(self, answer: bool, market: AgentMarket) -> BetAmount:
        amount: Decimal
        max_bet_amount: float
        if isinstance(market, ManifoldAgentMarket) :
            # Manifold won't give us fractional Mana, so bet the minimum amount to win at least 1 Mana.
            amount = market.get_minimum_bet_to_win(answer, amount_to_win=1) 
            max_bet_amount = 10.0
        else:
            # Otherwise, bet to win at least 0.001 (of something), unless the bet would be less than the tiny bet.
            amount = max(
                Decimal(minimum_bet_to_win(answer, amount_to_win=0.001, market=market)), 
                market.get_tiny_bet_amount().amount,
            )
            max_bet_amount = 0.01
        if amount > max_bet_amount:
            print(f"Would need at least {amount} {market.currency} to be profitable, betting only {market.get_tiny_bet_amount()} for benchmark purposes.")
            amount = market.get_tiny_bet_amount().amount
        return BetAmount(amount=amount, currency=market.currency)

    def answer_binary_market(self, market: AgentMarket) -> bool:
        prediciton = self.agent.predict(market.question)  # Already checked in the `pick_markets`.
        if prediciton.outcome_prediction is None:
            raise ValueError(f"Missing prediction: {prediciton}")
        binary_answer: bool = prediciton.outcome_prediction.p_yes > 0.5
        print(f"Answering '{market.question}' with '{binary_answer}'.")
        return binary_answer
    

class DeployableAgentER_EvoGPT3(DeployableAgentER):
    agent = EvoAgent(model="gpt-3.5-turbo-0125")


class DeployableAgentER_OlasEmbeddingOA(DeployableAgentER):
    agent = OlasAgent(model="gpt-3.5-turbo-0125", embedding_model=EmbeddingModel.openai)
