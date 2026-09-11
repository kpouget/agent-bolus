#!/usr/bin/env python3
"""
Analyze all I:C ratios for all periods and save results to output directory
"""
import sys
import asyncio
import os
sys.path.append('nooa')

async def analyze_and_save_all_periods():
    """Run I:C ratio analysis for all periods and save results."""
    print("🧪 Analyse des Ratios I:C - Toutes les Périodes")
    print("=" * 50)

    try:
        from dotenv import load_dotenv
        from nooa.unifiedllm.registry import get_llm_client
        from ratio_analysis_agent import RatioAnalysisAgent

        # Load environment
        load_dotenv()

        print(f"🔧 Setting up LLM client...")

        # Create LLM client
        llm = get_llm_client(
            f"openai/{os.getenv('MODEL_NAME')}",
            api_base=os.getenv('MODEL_URL'),
            api_key=os.getenv('ACCESS_KEY')
        )

        # Create analysis agent
        agent = RatioAnalysisAgent("analysis_patient", llm=llm)
        print(f"✅ RatioAnalysisAgent created")

        # Set up file paths
        filepath = "data/csv_report_30days-20260911_102845.csv"
        output_dir = "output"

        if not os.path.exists(filepath):
            print(f"❌ Data file not found: {filepath}")
            return

        # Run analysis for all periods
        print(f"📊 Analyse des 7 derniers jours de données diabète...")
        print(f"📁 Résultats sauvegardés dans: {output_dir}/")

        results = await agent.analyze_all_periods_and_save(
            filepath=filepath,
            days_back=7,
            output_dir=output_dir
        )

        # Show summary
        print(f"\n📈 Analysis Summary:")
        for period, summary in results["summary"].items():
            recommendation = summary["primary_recommendation"]
            confidence = summary["confidence"]
            has_llm = "✅" if summary["has_llm_analysis"] else "⚠️"
            print(f"   {period}: {recommendation} (confidence: {confidence:.1%}) {has_llm}")

        print(f"\n📁 Files saved:")
        for file_path in results["saved_files"]:
            print(f"   {file_path}")

        print(f"\n🎯 Types de fichiers générés pour chaque période:")
        print(f"   📊 *_plot_data_*.yaml - Données prêtes pour visualisation")
        print(f"   🩸 *_bg_detailed_*.yaml - Lectures de glycémie individuelles")
        print(f"   📝 *_llm_analysis_*.md - Analyse LLM en français")
        print(f"   💾 *_7days_*.yaml - Données complètes d'analyse")

        print(f"\n✅ Analyse terminée! Vérifiez le répertoire '{output_dir}/' pour les résultats.")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(analyze_and_save_all_periods())