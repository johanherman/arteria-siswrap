#import pytest
#import tornado.web
#import jsonpickle
#from arteria import *
#from arteria.configuration import ConfigurationService
#from siswrap.app import *
#from siswrap.handlers import *
#from siswrap.wrapper_services import *


class TestHelpers(object):

    SISYPHUS_CONFIG = """MISMATCH:
        1: 1
        2: 1
        3: 1
        4: 1
        5: 1
        6: 1
        7: 1
        8: 1

# The host on which to put the summaries
SUMMARY_HOST: mm-xlas002

# The directory on ARCHIVE_HOST to put the runfolder in
SUMMARY_PATH: /mnt/Seq-Summaries/2015/

# The path, relative to the runfolder, where MiSeq analysis output is deposited

# The maximum error in a lane before filtering out bad tiles (%)
MAX_LANE_ERROR: 2

# The maximum error in a tile in a lane with too high error (%)
MAX_TILE_ERROR: 2"""

    QC_CONFIG = """<QCrequirements>
	<platforms>
		<platform>
			<controlSoftware>HiSeq Control Software</controlSoftware>
			<version>HiSeq Flow Cell v3</version>
			<mode>HighOutput</mode>
			<unidentified>20.0</unidentified>
			<overridePoolingRequirement>0</overridePoolingRequirement>
			<lengths>
			</lengths>
			<warning>
				<unidentified>5.0</unidentified>
				<numberOfCluster>140</numberOfCluster>
				<overridePoolingRequirement>0</overridePoolingRequirement>
				<lengths>
					<l100>
						<q30>11</q30>
						<errorRate>2.0</errorRate>
					</l100>
					<l101>
						<q30>11</q30>
						<errorRate>2.0</errorRate>
					</l101>
					<l50>
						<q30>5.6</q30>
						<errorRate>1.0</errorRate>
					</l50>
					<l51>
						<q30>5.6</q30>
						<errorRate>1.0</errorRate>
					</l51>
				</lengths>
			</warning>
		</platform>
		<platform>
			<controlSoftware>HiSeq Control Software</controlSoftware>
			<version>HiSeq Flow Cell v4</version>
			<mode>RapidHighOutput</mode>
			<unidentified>20.0</unidentified>
			<overridePoolingRequirement>0</overridePoolingRequirement>
			<lengths>
			</lengths>
			<warning>
				<unidentified>10.0</unidentified>
				<numberOfCluster>180</numberOfCluster>
				<overridePoolingRequirement>0</overridePoolingRequirement>
				<lengths>
					<l125>
						<q30>18</q30>
						<errorRate>2.0</errorRate>
					</l125>
   					<l126>
                         <q30>18</q30>
                        <errorRate>2.0</errorRate>
                    </l126>
					<l100>
						<q30>14</q30>
						<errorRate>2.0</errorRate>
					</l100>
					<l101>
						<q30>14</q30>
						<errorRate>2.0</errorRate>
					</l101>
					<l50>
						<q30>7.0</q30>
						<errorRate>1.0</errorRate>
					</l50>
					<l51>
						<q30>7.0</q30>
						<errorRate>1.5</errorRate>
					</l51>
					<l62>
						<q30>7.0</q30>
						<errorRate>1.5</errorRate>
					</l62>
				</lengths>
			</warning>
		</platform>
		 <platform>
                        <controlSoftware>HiSeq X Control Software</controlSoftware>
                        <version>HiSeq X HD v2</version>
                        <unidentified>25.0</unidentified>
                        <overridePoolingRequirement>0</overridePoolingRequirement>
                        <lengths>
                        </lengths>
                        <warning>
                                <unidentified>10.0</unidentified>
                                <numberOfCluster>300</numberOfCluster>
                                <overridePoolingRequirement>0</overridePoolingRequirement>
                                <lengths>
                                        <l151>
                                                <q30>33.7</q30>
                                                <errorRate>5.0</errorRate>
                                        </l151>
                                </lengths>
                        </warning>
                </platform>
		<platform>
			<controlSoftware>HiSeq Control Software</controlSoftware>
			<version>HiSeq Rapid Flow Cell v1</version>
			<mode>RapidRun</mode>
			<unidentified>20.0</unidentified>
			<overridePoolingRequirement>0</overridePoolingRequirement>
			<lengths>
			</lengths>
			<warning>
				<unidentified>10.0</unidentified>
				<numberOfCluster>110</numberOfCluster>
				<overridePoolingRequirement>0</overridePoolingRequirement>
				<lengths>
					<l151>
						<q30>12.3</q30>
						<errorRate>2.0</errorRate>
					</l151>
					<l101>
						<q30>8.8</q30>
						<errorRate>2.0</errorRate>
					</l101>
				</lengths>
			</warning>
		</platform>
		<platform>
			<controlSoftware>HiSeq Control Software</controlSoftware>
			<version>HiSeq Rapid Flow Cell v2</version>
			<mode>RapidRun</mode>
			<unidentified>20.0</unidentified>
			<overridePoolingRequirement>0</overridePoolingRequirement>
			<lengths>
			</lengths>
			<warning>
				<unidentified>10.0</unidentified>
				<numberOfCluster>110</numberOfCluster>
				<overridePoolingRequirement>0</overridePoolingRequirement>
				<lengths>
					<l251>
						<q30>18.7</q30>
						<errorRate>5.0</errorRate>
					</l251>
					<l250>
						<q30>18.7</q30>
						<errorRate>5.0</errorRate>
					</l250>
					<l151>
						<q30>12.3</q30>
						<errorRate>2.0</errorRate>
					</l151>
					<l101>
						<q30>8.8</q30>
						<errorRate>2.0</errorRate>
					</l101>
				</lengths>
			</warning>
		</platform>
		<platform>
			<controlSoftware>MiSeq Control Software</controlSoftware>
			<version>Version2</version>
			<unidentified>20.0</unidentified>
			<overridePoolingRequirement>0</overridePoolingRequirement>
			<lengths>
			</lengths>
			<warning>
				<unidentified>10.0</unidentified>
				<numberOfCluster>10</numberOfCluster>
				<overridePoolingRequirement>0</overridePoolingRequirement>
				<lengths>
					<l251>
						<q30>1.8</q30>
						<errorRate>5.0</errorRate>
					</l251>
					<l151>
						<q30>1.1</q30>
						<errorRate>2.0</errorRate>
					</l151>
					<l26>
						<q30>0.2</q30>
						<errorRate>1.0</errorRate>
					</l26>
				</lengths>
			</warning>
		</platform>
		<platform>
			<controlSoftware>MiSeq Control Software</controlSoftware>
			<version>Version3</version>
			<unidentified>20.0</unidentified>
			<overridePoolingRequirement>0</overridePoolingRequirement>
			<lengths>
			</lengths>
			<warning>
				<unidentified>10.0</unidentified>
				<numberOfCluster>18</numberOfCluster>
				<overridePoolingRequirement>0</overridePoolingRequirement>
				<lengths>
					<l301>
						<q30>3.7</q30>
						<errorRate>5.0</errorRate>
					</l301>
					<l75>
						<q30>1.1</q30>
						<errorRate>1.5</errorRate>
					</l75>
				</lengths>
			</warning>
		</platform>
	</platforms>
	<overrides>
		<warning>
			<lane1>
			</lane1>
		</warning>
		<pass>
			<lane1>
			</lane1>
		</pass>
	</overrides>
</QCrequirements>"""
