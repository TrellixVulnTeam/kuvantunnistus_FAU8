mkdir /recognition &&
cd /recognition &&
git clone codecommit://vaylaapp@git-codecommit.eu-west-1.amazonaws.com/v1/repos/kuvatieto-vieraslaji-docker &&
python3 ./poll_recognition_queue.py 

aws ecs register-task-definition --cli-input-json file://ecs-vieraslaji-cpu-inference-taskdef.json --profile vaylaapp

aws ecs create-service --cluster kuvatieto-analytics-qa \
                       --service-name cli-ec2-inference-cpu \
                       --task-definition Ec2TFInference:revision_id \
                       --desired-count 1 \
                       --launch-type EC2 \
                       --scheduling-strategy="REPLICA" \
                       --region us-east-1

aws ecs create-service --cluster kuvatieto-analytics-qa \
                       --service-name cli-ec2-inference-cpu \
                       --task-definition Ec2TFInference:revision_id \
                       --desired-count 1 \
                       --launch-type EC2 \
                       --scheduling-strategy="REPLICA" \
                       --region us-east-1
